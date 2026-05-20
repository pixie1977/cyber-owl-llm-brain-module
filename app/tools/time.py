"""
Модуль для получения текущего времени в текстовом виде.
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
        str: Текущее время (например, "15:42").
    """
    return datetime.now().strftime("%H:%M")


@tool
def get_current_time_as_str(**kwargs) -> tuple[str, bool]:
    """
    Возвращает текущее время словами на русском языке.

    Вызывайте ТОЛЬКО при прямом вопросе: «который час?», «сколько времени?» и т.п.

    Args:
        **kwargs: Игнорируемые аргументы (совместимость с LangChain).

    Returns:
        tuple[str, bool]: Кортеж из текстового времени и флага завершения цепочки.
    """
    current_time = get_time()
    log.info("Инструмент вызван: get_current_time -> %s", current_time)
    str_time = Utils.time_as_words()
    return str_time, True