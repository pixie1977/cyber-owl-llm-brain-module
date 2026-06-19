"""
Модуль для загрузки и случайного выбора шуток из файла.
"""
from langchain_core.tools import tool

from app.tools.common_data.jokes_provider import get_joke


@tool
def joke_tool(**kwargs) -> tuple[str, bool]:
    """
    Возвращает случайную шутку. Вызывается, когда пользователь просит пошутить.

    Используется при запросах: пошути, анекдот, расскажи смешное и т.п.

    :param kwargs: Игнорируемые именованные аргументы.
    :return: Кортеж из шутки и флага успешности.
    """
    return get_joke(), True