import asyncio
import gc
import os
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.data.data import FaceDetection
from app.core.llm.llm import process_request_with_llm
from app.core.logger import get_logger
from app.core.logic.vector_search import VectorSearch
from app.integration.integration_adapter import (
    send_mat_sign_servo,
    send_ready_servo,
    send_to_tts,
    send_lw_up,
    send_lw_down,
)
from app.integration.client import PostClient
from app.tools.brawl import get_mat_count, trigger_violent_mode
from app.tools.common_data.context_common import get_common_context
from app.tools.common_data.context_psychology import get_psychology_phrase
from app.tools.greetengs import get_greetengs
from app.core.logic.shuffle_bag import ShuffleBag
from app.utils.text.basic_text_utils import find_and_crop_by_keywords
from app.utils.text.expression_language_detector import RussianExpressionLanguageDetector
from app.utils.text.levenstein_text_utils import similarity_ratio
from app.config.config import FACE_URL

# --- Мониторинг памяти ---
_MEMORY_WARN_THRESHOLD_MB = 500  # предупреждение при >500MB
_last_mem_warn_request = 0  # для throttle предупреждений

# --- Настройка логирования ---
log = get_logger(__name__)

# --- Глобальные переменные ---
latest_question: Optional[str] = None
latest_response: Optional[str] = None
last_user_question: Optional[str] = None  # Для корректной эхо-проверки

# --- Константы времени (секунды) ---
GREETING_COOLDOWN_SECONDS = 600  # 10 минут между обычными фразами
DAILY_COOLDOWNS_SECONDS = 86400  # 24 часа для "ежедневных" событий (заготовка на будущее)
VECTOR_PHRASE_COOLDOWN_SECONDS = 300  # 5 минут между повторением фраз из векторного поиска
VECTOR_SIMILARITY_THRESHOLD = 0.9  # Повышенный порог для векторного поиска
ECHO_SIMILARITY_THRESHOLD = 0.5  # Порог эхо-проверки: "как дела" vs "как жизнь" = 0.75 → не эхо

# --- Стоп-команды для немедленной остановки озвучки ---
STOP_COMMANDS = ["стоп", "молчи", "хватит", "замолчи", "прекрати", "stop", "quiet", "silence"]

# --- Команды для запоминания лица ---
REGISTER_COMMANDS = ["запомни", "запомни меня", "я -", "меня зовут", "моё имя", "зови меня"]

# --- Паттерны для извлечения имени ---
NAME_PATTERNS = [
    r"(?:я|меня зовут|моё имя|зови меня)[\s—–-]+([А-Яа-яЁёA-Za-z]+(?:[\s—–-][А-Яа-яЁёA-Za-z]+)*)",
    r"запомни(?:\s+меня)?[\s,.-]+(?:меня\s+)?(?:зовут|имя)[\s—–-]+([А-Яа-яЁёA-Za-z]+)",
    r"запомни(?:\s+меня)?[\s,.-]+([А-Яа-яЁёA-Za-z]+)",
]

# --- История произнесённых фраз ---
_recent_phrases: list = []  # [(phrase, timestamp), ...]
_MAX_RECENT_PHRASES = 20


def _is_phrase_recent(phrase: str, cooldown: float = VECTOR_PHRASE_COOLDOWN_SECONDS) -> bool:
    """Проверяет, не произносилась ли уже эта фраза недавно."""
    current_time = time.time()
    _recent_phrases[:] = [
        (p, t) for p, t in _recent_phrases
        if current_time - t < cooldown
    ]
    for p, _ in _recent_phrases:
        if similarity_ratio(phrase, p) > 0.85:
            return True
    return False


def _record_phrase(phrase: str) -> None:
    """Добавляет фразу в историю произнесённых."""
    _recent_phrases.append((phrase, time.time()))
    if len(_recent_phrases) > _MAX_RECENT_PHRASES:
        _recent_phrases.pop(0)


def _check_memory() -> None:
    """Проверяет использование памяти и логгирует предупреждение при превышении порога."""
    global _last_mem_warn_request
    try:
        import resource
        usage_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
        if usage_mb > _MEMORY_WARN_THRESHOLD_MB:
            now = time.time()
            if now - _last_mem_warn_request > 60:  # throttle: раз в минуту
                log.warning(f"Использование памяти: {usage_mb}MB (порог: {_MEMORY_WARN_THRESHOLD_MB}MB)")
                _last_mem_warn_request = now
    except (ImportError, AttributeError):
        # resource не доступен на Windows
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            usage_mb = proc.memory_info().rss // (1024 * 1024)
            if usage_mb > _MEMORY_WARN_THRESHOLD_MB:
                now = time.time()
                if now - _last_mem_warn_request > 60:
                    log.warning(f"Использование памяти: {usage_mb}MB (порог: {_MEMORY_WARN_THRESHOLD_MB}MB)")
                    _last_mem_warn_request = now
        except ImportError:
            pass


# --- Список персонажей ---
PERSONALITIES: List[Dict[str, Any]] = [
    {
        "name": "Мастер",
        "aliases": ["eugen", "eugen-1", "eugen-2", "eugen-3", "eugen-4"],
        "id": "master",
        "alignment": "loyal",
        "last_timestamp": 0,
        "greeting": [
            "Приветствую, Мастер!",
            "Здравствуйте, Мастер.",
            "Мастер, пусть у тебя всё сложится сегодня."
        ],
        "phrases": [
            "Мастер, всех и всегда посылай в манду. И не жди, пока тебя пошлют н+а хер.",
            "Мастер! Не унывай!",
            "Ты можешь сделать это.",
            "Женя, сколько будет пятью пять?",
            "Сам ты чучело!"
        ],
    },
    {
        "name": "Володя",
        "aliases": ["vova", "vova-1", "vova-2", "vova-3", "vova-4"],
        "id": "boatsman",
        "alignment": "loyal",
        "last_timestamp": 0,
        "greeting": [
            "Вова! Привет!",
            "Здравствуйте, боцман.",
            "Пусть у тебя всё сложится сегодня.",
        ],
        "phrases": [
            "Пошли в фу-сян!",
            "Ты сейчас Володя или Володька?",
            "А какого карпа ты упустил последний раз! Мне прям радостно.",
            "Не спи, старый! Молодежь на пятки наступает!",
        ],
    },
]


class State(Enum):
    """Состояния поведенческого автомата."""
    STARTED = -5
    READY = 0
    ANSWERING = 10
    SLEEPING = 20
    IMAGE_REACTION = 30


class Behaviour:
    """Асинхронный менеджер поведения: обработка речи, лиц, выражений."""

    def __init__(self, interval_seconds: float = 0.1) -> None:
        self.interval = interval_seconds
        self.query_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.img_queue: asyncio.Queue[List[FaceDetection]] = asyncio.Queue()
        self.expression_detector = RussianExpressionLanguageDetector()
        self.common_vector_search = VectorSearch(get_common_context())
        self.state: State = State.SLEEPING
        self.is_running = False
        self.counter: int = 0
        self._current_tts_task: Optional[asyncio.Task] = None
        self._abort_processing: bool = False
        self._last_faces: List[FaceDetection] = []

    # ——— Основной цикл ———
    async def _loop(self) -> None:
        """Цикл обработки состояний."""
        while self.is_running:
            try:
                if self.state == State.STARTED:
                    await send_ready_servo()
                    await self._speak(get_greetengs())
                    self.state = State.READY

                elif self.state == State.READY:
                    res = self._try_transition_from_ready()
                    self.counter += res
                    if res == 0:
                        self.counter = 0
                    if self.counter > 600:
                        await self._speak(get_psychology_phrase())
                    if res > 0:
                        await asyncio.sleep(0.5)

                elif self.state == State.ANSWERING:
                    item = await self.query_queue.get()
                    # Проверяем сигнал отмены в очереди
                    if isinstance(item, dict) and item.get("_abort"):
                        log.info("Получен сигнал отмены из очереди")
                        self.state = State.READY
                        continue
                    await self._process_user_query(item)
                    self.state = State.READY

                elif self.state == State.IMAGE_REACTION:
                    faces = await self.img_queue.get()
                    await self._process_image(faces)
                    self.state = State.READY

            except Exception as e:
                log.error("Ошибка в поведенческом цикле: %s", e)
                await asyncio.sleep(0.5)

    def _try_transition_from_ready(self) -> int:
        """Переход из READY в ANSWERING или IMAGE_REACTION."""
        if not self.query_queue.empty():
            self.state = State.ANSWERING
            return 0
        elif not self.img_queue.empty():
            self.state = State.IMAGE_REACTION
            return 0
        else:
            return 1

    # ——— Управление TTS ———
    async def _speak(self, text: str) -> None:
        """
        Запускает озвучку текста как фоновую задачу.
        НЕ блокирует event loop — возвращаетcя сразу.
        Предыдущая задача отменяется, если ещё не завершена.
        """
        # Отменяем предыдущую задачу TTS, если она ещё активна
        if self._current_tts_task and not self._current_tts_task.done():
            log.info("Отмена текущей озвучки перед новой")
            self._current_tts_task.cancel()
            try:
                await self._current_tts_task
            except asyncio.CancelledError:
                pass
            finally:
                self._current_tts_task = None

        # Запускаем новую задачу — НЕ ждём завершения
        self._current_tts_task = asyncio.create_task(send_to_tts(text))

    async def cancel_current_tts(self) -> None:
        """
        Немедленно отменяет текущую озвучку и помечает запрос на прерывание.
        НЕ блокируется — просто отменяет задачу.
        """
        self._abort_processing = True
        # Помещаем сигнал отмены в очередь — _process_user_query его поймает
        await self.query_queue.put({"_abort": True})

        if self._current_tts_task and not self._current_tts_task.done():
            log.info("Принудительная отмена текущей озвучки")
            self._current_tts_task.cancel()
            # Не ждём завершения — просто отменяем
            self._current_tts_task = None

    # ——— Запоминание лиц ———
    def _is_stop_command(self, text: str) -> bool:
        """
        Проверяет, является ли фраза стоп-командой.

        Args:
            text: Текст фразы (в нижнем регистре).

        Returns:
            True, если это стоп-команда.
        """
        return any(cmd in text for cmd in STOP_COMMANDS)

    def _extract_name_from_text(self, text: str) -> Optional[str]:
        """
        Извлекает имя из фразы пользователя.

        Args:
            text: Текст фразы (в нижнем регистре).

        Returns:
            Имя в корректном регистре или None, если не найдено.
        """
        for pattern in NAME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Делаем первую букву заглавной
                return name.capitalize()
        return None

    def _is_register_command(self, text: str) -> bool:
        """
        Проверяет, является ли фраза командой для запоминания лица.

        Args:
            text: Текст фразы (в нижнем регистре).

        Returns:
            True, если это команда для запоминания.
        """
        return any(cmd in text for cmd in REGISTER_COMMANDS)

    async def register_face(self, name: str) -> bool:
        """
        Регистрирует лицо с указанным именем на видеомодуле.

        Args:
            name: Имя для регистрации.

        Returns:
            True, если регистрация успешна.
        """
        if not self._last_faces:
            log.warning("Нет обнаруженных лиц для регистрации")
            return False

        if len(self._last_faces) != 1:
            log.warning(f"Ожидается 1 лицо для регистрации, найдено {len(self._last_faces)}")
            return False

        face = self._last_faces[0]
        bbox = face.bbox

        log.info(f"Регистрация лица: {name}, bbox={bbox}, confidence={face.confidence}")

        # Формируем тело запроса для видеомодуля
        payload = {
            "username": name.lower().replace(" ", "_")
        }

        try:
            async with PostClient(FACE_URL) as client:
                success = await client.post_register(payload)
            if success:
                log.info(f"Лицо '{name}' успешно зарегистрировано в видеомодуле")
                return True
            else:
                log.error(f"Ошибка регистрации лица '{name}'")
                return False
        except Exception as e:
            log.error(f"Ошибка при отправке запроса на регистрацию лица: {e}")
            return False

    # ——— Обработка запросов ———
    async def _process_user_query(self, item: Dict[str, Any]) -> None:
        """Генерирует и озвучивает ответ по текстовому запросу."""
        global latest_response
        await send_lw_up()
        query = item.get("query")
        expression = item.get("expression")
        mat_count = get_mat_count(expression)

        response = ""

        if mat_count > 0:
            raw_res = await trigger_violent_mode.ainvoke({})
            response = raw_res[0] if isinstance(raw_res, tuple) else str(raw_res)

        if self._abort_processing:
            log.info("Обработка прервана по стоп-команде")
            await send_lw_down()
            return

        if not response:
            response = self.common_vector_search.find_answer(query)

        if self._abort_processing:
            log.info("Обработка прервана по стоп-команде")
            await send_lw_down()
            return

        if not response or response == "None":
            response = await process_request_with_llm(
                item.get("query"),
                item.get("expression"),
            )

        if self._abort_processing:
            log.info("Обработка прервана по стоп-команде")
            await send_lw_down()
            return

        if response.strip():
            latest_response = response
            await self._speak(response)
        await send_lw_down()

    async def post_user_query(self, request: str) -> None:
        """Обрабатывает и ставит в очередь пользовательский запрос."""
        self._abort_processing = False
        try:
            await self._post_user_query_impl(request)
        except Exception as e:
            log.error("Ошибка в post_user_query: %s", e, exc_info=True)

    async def _post_user_query_impl(self, request: str) -> None:
        """Реальная логика обработки пользовательского запроса."""
        global latest_question, latest_response, last_user_question

        # Принудительная сборка мусора перед обработкой
        gc.collect()

        raw_question = request.strip().lower()

        # Быстрая реакция на стоп-команды
        if any(cmd in raw_question for cmd in STOP_COMMANDS):
            log.info("Стоп-команда обнаружена, останавливаю TTS: %s", raw_question)
            await self.cancel_current_tts()
            return

        # Проверка команды запоминания лица
        if self._is_register_command(raw_question):
            extracted_name = self._extract_name_from_text(raw_question)
            if extracted_name:
                log.info(f"Обнаружена команда запоминания лица: {extracted_name}")
                success = await self.register_face(extracted_name)
                if success:
                    await self._speak(f"Хорошо, я запомнил тебя, {extracted_name}.")
                else:
                    await self._speak("Я не вижу лица в кадре, чтобы запомнить.")
                return
            else:
                log.warning("Не удалось извлечь имя из фразы")
                await self._speak("Пожалуйста, скажи своё имя чётче.")
                return

        expression = self.expression_detector.analyze(raw_question)
        mat_count = get_mat_count(expression)
        if mat_count > 0:
            await send_mat_sign_servo(mat_count)

        # Очистка от ключевых слов
        question = find_and_crop_by_keywords(
            key_words=["орбиту","орбита","альма","агата","марта","камрад", "камрат", "шалунья", "совушка", "совунья", "чувырло", "чучело"],
            text=raw_question,
            threshold=80,
        )

        # Эхо-проверка: сравниваем текущий вопрос с ПОСЛЕДНИМ вопросом пользователя,
        # а не с ответом бота — это предотвращает сброс при векторном поиске
        # Порог 0.8: "камрад как дела" vs "камрад как жизнь" = 0.75 сходства → не эхо
        is_not_echo = True #bool(similarity_ratio(raw_question, last_user_question or "") < ECHO_SIMILARITY_THRESHOLD)

        log.info(f"Последний вопрос: {last_user_question}. Текущий вопрос: {raw_question}. Проверка на эхо: {is_not_echo}")

        if not question and is_not_echo:
            # Если вопрос не содержит интересующих нас фраз, проверяем векторный поиск
            response = self.common_vector_search.find_answer(raw_question)
            if response and response.strip() and response != "None":
                # Проверяем, не произносили ли уже эту фразу недавно
                if _is_phrase_recent(response):
                    log.info(f"Фраза уже произносилась недавно, пропускаем: {response}")
                    return
                log.info(f"Совпадение по быстрому векторному поиску!")
                latest_response = response
                last_user_question = raw_question
                _record_phrase(response)
                await self._speak(response)
            # Очистка после векторного поиска
            del response
            gc.collect()
            return

        if not question:
            return

        latest_question = question
        last_user_question = raw_question
        if is_not_echo:
            await self.query_queue.put({"query": question, "expression": expression})

        # Мониторинг памяти после обработки запроса
        _check_memory()

        # Освобождаем память
        del raw_question, expression, mat_count, question
        gc.collect()

        # Сбрасываем флаг прерывания для следующего запроса
        self._abort_processing = False

    # ——— Обработка лиц ———
    async def _process_image(self, faces: List[FaceDetection]) -> None:
        """Обрабатывает список распознанных лиц."""
        current_time = time.time()
        for face in faces:
            name = face.get("name") if isinstance(face, dict) else getattr(face, "name", None)
            if not name:
                continue

            person = self._get_known_person(name)
            if not person:
                continue

            await self._handle_known_person_meeting(person, current_time)

    def _get_known_person(self, name: str) -> Optional[Dict[str, Any]]:
        """Возвращает данные персонажа по имени или псевдониму."""
        return next(
            (p for p in PERSONALITIES if name in p["aliases"]),
            None,
        )

    def _create_greeting_bag(self, person: Dict[str, Any], first_meeting: bool) -> ShuffleBag:
        """Создаёт ShuffleBag с фразами: приветствие или реплика."""
        if first_meeting:
            return ShuffleBag(person["greeting"])
        else:
            return ShuffleBag(person["phrases"])

    async def _handle_known_person_meeting(
        self, person: Dict[str, Any], current_time: float
    ) -> None:
        """Определяет, нужно ли говорить приветствие или фразу, и делает это."""
        last_seen = float(person["last_timestamp"])

        first_meeting = last_seen == 0
        is_cooldown_passed = current_time - last_seen > GREETING_COOLDOWN_SECONDS

        if first_meeting or is_cooldown_passed:
            greeting_bag = self._create_greeting_bag(person, first_meeting)
            person["last_timestamp"] = current_time
            phrase = greeting_bag.pick()
            await self._speak(phrase)
            log.debug(
                "Выдана фраза '%s' для %s (первое встречное: %s)",
                phrase,
                person["name"],
                first_meeting,
            )

    # ——— Управление жизненным циклом ———
    async def post_faces(self, faces: List[FaceDetection]) -> None:
        """Добавляет изображение с лицами в очередь обработки."""
        try:
            # Сохраняем последнее обнаруженное лицо
            self._last_faces = list(faces)
            log.info(f"Обнаружено {len(faces)} лиц. Последнее: {[f.get('name') if isinstance(f, dict) else getattr(f, 'name', 'unknown') for f in faces]}")
            await self.img_queue.put(faces.copy())
        except Exception as e:
            log.error("Ошибка в post_faces: %s", e, exc_info=True)

    async def post_user_query_direct(self, request: str) -> None:
        """
        Прямой вызов обработки запроса из основного event loop.
        Используется для синхронных вызовов (например, из тестов).
        """
        self._abort_processing = False
        try:
            await self._post_user_query_impl(request)
        except Exception as e:
            log.error("Ошибка в post_user_query_direct: %s", e, exc_info=True)

    def start(self) -> None:
        """
        Запуск поведенческого автомата.
        Запускает _loop() в текущем event loop.
        Должен вызываться из async-контекста.
        """
        if not self.is_running:
            self.is_running = True
            self.state = State.STARTED
            log.info("Behaviour запущен в текущем event loop")

    def stop(self) -> None:
        """Остановка поведенческого автомата."""
        if self.is_running:
            self.is_running = False
            log.info("Behaviour остановлен")