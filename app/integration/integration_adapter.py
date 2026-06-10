"""
Модуль для взаимодействия с внешними сервисами: TTS и сервоприводы.
"""

import asyncio
import time

from app.config.config import SERVO_URL, TTS_URL
from app.core.logger import get_logger
from app.integration.client import PostClient
from app.utils.text.basic_text_utils import wrap_answer_with_ssml

# --- Настройка логирования ---
log = get_logger(__name__)

# --- Константы для позиций сервоприводов ---
MAT_DETECTED_START = {"hv": 100, "hh": 16, "lw": 55, "rw": 0}
MAT_DETECTED_RW_UP = {"hv": 100, "hh": 16, "lw": 55, "rw": 100}
MAT_DETECTED_RW_DOWN = {"hv": 100, "hh": 16, "lw": 55, "rw": 0}
MAT_DETECTED_END = {"hv": 50, "hh": 50, "lw": 55, "rw": 50}

LW_UP = {"hv": 100, "hh": 50, "lw": 100, "rw": 55}
LW_DOWN = {"hv": 100, "hh": 50, "lw": 0, "rw": 55}


async def send_to_tts(text: str) -> None:
    """
    Отправляет озвученный текст в TTS-сервис с SSML-обёрткой.

    Args:
        text: Текст для озвучивания.
    """
    try:
        wrapped_text = wrap_answer_with_ssml(text)
        async with PostClient(TTS_URL) as client:
            post_result = await client.post(text=wrapped_text)
        log.info("Результат отправки в TTS: %s", post_result)
    except Exception as e:
        log.error("Ошибка при отправке в TTS: %s", e)


async def send_to_servo(data: dict, url: str) -> None:
    """
    Отправляет JSON-данные на указанный URL (сервопривод).

    Args:
        data: Словарь с позициями сервоприводов.
        url: URL эндпоинта.
    """
    try:
        async with PostClient(url) as client:
            post_result = await client.post_json(json=data)
        log.info("Результат отправки в сервопривод: %s", post_result)
    except Exception as e:
        log.error("Ошибка при отправке в сервопривод: %s", e)


async def send_ready_servo() -> None:
    url = f"{SERVO_URL}/sleep"
    await send_to_servo(data={}, url=url)
    await asyncio.sleep(1)
    url = f"{SERVO_URL}/happy"
    await send_to_servo(data={}, url=url)


async def send_mat_sign_servo(count: int) -> None:
    """
    Выполняет анимацию жеста «козы» через сервоприводы.

    Args:
        count: Количество повторений движения.
    """
    url = f"{SERVO_URL}/set_positions"
    await send_to_servo(data=MAT_DETECTED_START, url=url)

    for _ in range(count):
        await send_to_servo(data=MAT_DETECTED_RW_UP, url=url)
        await asyncio.sleep(0.5)
        await send_to_servo(data=MAT_DETECTED_RW_DOWN, url=url)
        await asyncio.sleep(0.5)

    await send_to_servo(data=MAT_DETECTED_END, url=url)


async def send_lw_up() -> None:
    url = f"{SERVO_URL}/set_positions"
    await send_to_servo(data=LW_UP, url=url)


async def send_lw_down() -> None:
    url = f"{SERVO_URL}/set_positions"
    await send_to_servo(data=LW_DOWN, url=url)