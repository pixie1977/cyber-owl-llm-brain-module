import asyncio
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.data import FaceDetection
from app.core.llm import process_request_with_llm
from app.core.logger import get_logger
from app.integration.integration_adapter import (
    send_mat_sign_servo,
    send_ready_servo,
    send_to_tts,
)
from app.tools.brawl import get_mat_count
from app.tools.greetengs import get_greetengs
from app.utils.shuffle_bag import ShuffleBag
from app.utils.text.basic_text_utils import find_and_crop_by_keywords
from app.utils.text.expression_language_detector import RussianExpressionLanguageDetector
from app.utils.text.levenstein_text_utils import similarity_ratio

# --- Настройка логирования ---
log = get_logger(__name__)

# --- Глобальные переменные ---
latest_question: Optional[str] = None
latest_response: Optional[str] = None

GREETING_COOLDOWN_SECONDS = 600 # 10 минут
DAILY_COOLDOWNS_SECONDS = 60*60*24 # День

personalities_list = [
    {
        "name": "Мастер",
        "aliases": ["eugen", "eugen-1", "eugen-2", "eugen-3", "eugen-4"],
        "id": "master",
        "alignment": "loyal",
        "last_timestamp": 0,
        "greeting": ["Привет!", "Здравствуйте, мастер.", "Пусть у тебя вс сложится сегодня"],
        "phrases": ["Не унывай!", "Ты можешь сделать это."]

    },
    {
        "name": "Володя",
        "aliases": ["vova", "vova-1", "vova-2", "vova-3", "vova-4"],
        "id": "boatsman",
        "alignment": "loyal",
        "last_timestamp": 0,
        "greeting": ["Привет!", "Здравствуйте, боцман.", "Пусть у тебя вс сложится сегодня"],
        "phrases": ["Пошли в фу-сян!", "Ты сейчас Володя или Володька?", "А какого карпа ты упустил последний раз! Мне прям радостно.", "Молодежь на пятки наступает!"]
    },
]


class State(Enum):
    STARTED = -5
    READY = 0
    ANSWERING = 10
    SLEEPING = 20
    IMAGE_REACTION = 30


class Behaviour:
    """Асинхронный менеджер поведения с обработкой запросов и изображений."""

    def __init__(self, interval_seconds: float = 0.1) -> None:
        self.interval = interval_seconds
        self.query_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.img_queue: asyncio.Queue[List[FaceDetection]] = asyncio.Queue()
        self.expression_detector = RussianExpressionLanguageDetector()
        self.state: State = State.SLEEPING
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    async def _loop(self) -> None:
        """Основной асинхронный цикл поведения."""
        while self.is_running:
            try:
                if self.state == State.STARTED:
                    await send_ready_servo()
                    await send_to_tts(get_greetengs())
                    self.state = State.READY

                elif self.state == State.READY:
                    done = False
                    if not self.query_queue.empty():
                        self.state = State.ANSWERING
                        done = True
                    elif not self.img_queue.empty():
                        self.state = State.IMAGE_REACTION
                        done = True

                    if not done:
                        await asyncio.sleep(0.1)
                        continue

                elif self.state == State.ANSWERING:
                    item = await self.query_queue.get()
                    await self._process_user_query(item)
                    self.state = State.READY

                elif self.state == State.IMAGE_REACTION:
                    faces = await self.img_queue.get()
                    await self._process_image(faces)
                    self.state = State.READY

            except Exception as e:
                log.error(f"Ошибка в работе поведенческого модуля: {e}")
                await asyncio.sleep(0.5)

    async def _process_user_query(self, item: Dict[str, Any]) -> None:
        """Обработка текстового запроса пользователя."""
        global latest_response
        response = await process_request_with_llm(
            item.get("query"),
            item.get("expression"),
        )
        if response.strip():
            latest_response = response
            await send_to_tts(response)

    async def post_user_query(self, request: str) -> None:
        """Помещает пользовательский запрос в очередь на обработку."""
        global latest_question, latest_response
        question = request.strip()
        expression_score = self.expression_detector.analyze(question)
        mat_count = get_mat_count(expression_score)
        if mat_count > 0:
            await send_mat_sign_servo(mat_count)

        # Обрезаем по ключевым словам
        question = find_and_crop_by_keywords(
            key_words=["совунья", "чувырло", "чучело"],
            text=question,
            threshold=50,
        )

        if not question:
            return

        latest_question = question
        similarity_score = similarity_ratio(latest_question, latest_response or "")
        if similarity_score < 0.5:
            await self.query_queue.put({"query": question, "expression": expression_score})

    async def post_faces(self, faces: List[FaceDetection]) -> None:
        """Помещает список лиц в очередь на обработку."""
        await self.img_queue.put(faces.copy())

    def _start_async_loop(self) -> None:
        """Целевая функция для запуска асинхронного цикла в отдельном потоке."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._loop())
        finally:
            loop.close()

    def start(self) -> None:
        """Запускает поведенческий цикл."""
        if not self.is_running:
            self.is_running = True
            self.state = State.STARTED
            self._thread = threading.Thread(target=self._start_async_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Останавливает поведенческий цикл."""
        if self.is_running:
            self.is_running = False
            if self._thread:
                self._thread.join(timeout=2.0)

    async def _process_image(self, faces: List[FaceDetection]) -> None:
        """Реагирует на распознанные лица."""
        current_time = time.time()
        for face in faces:
            name = face.name
            known_person = next(
                (p for p in personalities_list if name in p["aliases"]),
                None,
            )
            if known_person:
                last_seen = float(known_person["last_timestamp"])
                greetings = None
                if last_seen == 0:
                    greetings = ShuffleBag(known_person["greeting"])
                elif current_time - last_seen > GREETING_COOLDOWN_SECONDS:  # 20 минут
                    greetings = ShuffleBag(known_person["phrases"])

                if greetings:
                    known_person["last_timestamp"] = current_time
                    await send_to_tts(greetings.pick())