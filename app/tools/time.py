"""
Модуль для получения текущего времени.
"""

from datetime import datetime

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.utils.utils import Utils


# --- Настройка логирования ---
log = get_logger(__name__)


def get_time() -> str:
    """
    Возвращает текущее время в формате ЧЧ:ММ.

    Returns:
        str: Текущее время в виде строки (например, "15:42").
    """
    return datetime.now().strftime("%H:%M")


@tool(return_direct=True)
def get_current_time_as_str(**kwargs) -> str:
    """
    Возвращает текущее время словами.

    Вызывай ТОЛЬКО если пользователь прямо спрашивает «который час» или «сколько времени».

    Args:
        **kwargs: Фиктивные аргументы (для совместимости с вызовом инструмента).

    Returns:
        str: Текущее время на русском языке (например, «двенадцать часов тридцать минут»).
    """
    current_time = get_time()
    log.info(f"Инструмент вызван: get_current_time -> {current_time}")
    str_time = Utils.time_as_words()
    return str_time