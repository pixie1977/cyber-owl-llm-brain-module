import asyncio
import time
import threading
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
from app.tools.brawl import get_mat_count, trigger_violent_mode
from app.tools.common_data.context_common import get_common_context
from app.tools.greetengs import get_greetengs
from app.core.logic.shuffle_bag import ShuffleBag
from app.utils.text.basic_text_utils import find_and_crop_by_keywords
from app.utils.text.expression_language_detector import RussianExpressionLanguageDetector
from app.utils.text.levenstein_text_utils import similarity_ratio

# --- Настройка логирования ---
log = get_logger(__name__)

# --- Глобальные переменные ---
latest_question: Optional[str] = None
latest_response: Optional[str] = None

# --- Константы времени (секунды) ---
GREETING_COOLDOWN_SECONDS = 600  # 10 минут между обычными фразами
DAILY_COOLDOWNS_SECONDS = 86400  # 24 часа для "ежедневных" событий (заготовка на будущее)


# --- Список персонажей ---
PERSONALITIES: List[Dict[str, Any]] = [
    {
        "name": "Мастер",
        "aliases": ["eugen", "eugen-1", "eugen-2", "eugen-3", "eugen-4"],
        "id": "master",
        "alignment": "loyal",
        "last_timestamp": 0,
        "greeting": [
            "Привет!",
            "Здравствуйте, мастер.",
            "Пусть у тебя всё сложится сегодня.",
        ],
        "phrases": [
            "Не унывай!",
            "Ты можешь сделать это.",
        ],
    },
    {
        "name": "Володя",
        "aliases": ["vova", "vova-1", "vova-2", "vova-3", "vova-4"],
        "id": "boatsman",
        "alignment": "loyal",
        "last_timestamp": 0,
        "greeting": [
            "Привет!",
            "Здравствуйте, боцман.",
            "Пусть у тебя всё сложится сегодня.",
        ],
        "phrases": [
            "Пошли в фу-сян!",
            "Ты сейчас Володя или Володька?",
            "А какого карпа ты упустил последний раз! Мне прям радостно.",
            "Молодежь на пятки наступает!",
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
        self._thread: Optional[threading.Thread] = None

    # ——— Основной цикл ———
    async def _loop(self) -> None:
        """Цикл обработки состояний."""
        while self.is_running:
            try:
                if self.state == State.STARTED:
                    await send_ready_servo()
                    await send_to_tts(get_greetengs())
                    self.state = State.READY

                elif self.state == State.READY:
                    await self._try_transition_from_ready()

                elif self.state == State.ANSWERING:
                    item = await self.query_queue.get()
                    await self._process_user_query(item)
                    self.state = State.READY

                elif self.state == State.IMAGE_REACTION:
                    faces = await self.img_queue.get()
                    await self._process_image(faces)
                    self.state = State.READY

            except Exception as e:
                log.error("Ошибка в поведенческом цикле: %s", e)
                await asyncio.sleep(0.5)

    async def _try_transition_from_ready(self) -> None:
        """Переход из READY в ANSWERING или IMAGE_REACTION."""
        if not self.query_queue.empty():
            self.state = State.ANSWERING
        elif not self.img_queue.empty():
            self.state = State.IMAGE_REACTION
        else:
            await asyncio.sleep(0.5)

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
            response = trigger_violent_mode()

        if not response:
            response = self.common_vector_search.find_answer(query)

        if not response or response == "None":
            response = await process_request_with_llm(
                item.get("query"),
                item.get("expression"),
            )

        if response.strip():
            latest_response = response
            await send_to_tts(response)
        await send_lw_down()

    async def post_user_query(self, request: str) -> None:
        """Обрабатывает и ставит в очередь пользовательский запрос."""
        global latest_question, latest_response

        raw_question = request.strip()
        expression = self.expression_detector.analyze(raw_question)
        mat_count = get_mat_count(expression)
        if mat_count > 0:
            await send_mat_sign_servo(mat_count)

        # Очистка от ключевых слов
        question = find_and_crop_by_keywords(
            key_words=["совушка", "совунья", "чувырло", "чучело"],
            text=raw_question,
            threshold=80,
        )

        is_not_echo = bool(similarity_ratio(question, latest_response or "") < 0.5)

        log.info(f"Последний ответ был: {latest_response}. Текущий вопрос: {question}. Проверка на эхо: {is_not_echo} ",)

        if not question and is_not_echo:
            # Если вопрос не содержит интересующих нас фраз, но содержит маркеры реакции
            response = self.common_vector_search.find_answer(raw_question)
            if response.strip():
                log.info(f"Совпадение по быстрому векторному поиску!")
                latest_response = response
                await send_to_tts(response)
            return

        if not question:
            return

        latest_question = question
        if is_not_echo:
            await self.query_queue.put({"query": question, "expression": expression})

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
            await send_to_tts(phrase)
            log.debug(
                "Выдана фраза '%s' для %s (первое встречное: %s)",
                phrase,
                person["name"],
                first_meeting,
            )

    # ——— Управление жизненным циклом ———
    async def post_faces(self, faces: List[FaceDetection]) -> None:
        """Добавляет изображение с лицами в очередь обработки."""
        await self.img_queue.put(faces.copy())

    def _start_async_loop(self) -> None:
        """Запуск цикла в отдельном потоке."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._loop())
        finally:
            loop.close()

    def start(self) -> None:
        """Запуск поведенческого автомата."""
        if not self.is_running:
            self.is_running = True
            self.state = State.STARTED
            self._thread = threading.Thread(target=self._start_async_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Остановка и ожидание завершения потока."""
        if self.is_running:
            self.is_running = False
            if self._thread:
                self._thread.join(timeout=2.0)