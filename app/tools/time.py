"""
Модуль для получения текущего времени.
"""

from datetime import datetime


def get_time() -> str:
    """
    Возвращает текущее время в формате ЧЧ:ММ.

    Returns:
        Текущее время в виде строки (например, "15:42").
    """
    current_time = datetime.now().strftime("%H:%M")
    return current_time