"""
Модуль для загрузки и случайного выбора шуток из файла.
"""

import logging
import os

from langchain_core.tools import tool

from app.utils.shuffle_bag import ShuffleBag

# Настройка логирования
logging.basicConfig()
logger = logging.getLogger(__name__)

# Путь к файлу с шутками
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
JOKES_FILE_PATH = os.path.join(CURRENT_DIRECTORY, "../data/jokes.txt")

# Глобальная переменная для хранения шуток
JOKES_SHUFFLE = None


def load_jokes() -> ShuffleBag:
    """
    Загружает шутки из файла и возвращает перемешанный контейнер (ShuffleBag).
    """
    logger.info("Загружаем шутки...")
    jokes_list = []

    with open(JOKES_FILE_PATH, "r", encoding="utf-8") as file:
        for line in file:
            cleaned_line = line.strip()
            if cleaned_line:  # Игнорируем пустые строки
                jokes_list.append(cleaned_line)

    logger.info("Загружено %d шуток.", len(jokes_list))
    return ShuffleBag(jokes_list)


def update_jokes() -> ShuffleBag:
    """
    Инициализирует или возвращает существующий экземпляр ShuffleBag с шутками.
    """
    global JOKES_SHUFFLE
    if JOKES_SHUFFLE is None:
        JOKES_SHUFFLE = load_jokes()
    return JOKES_SHUFFLE


def get_joke() -> str:
    """
    Возвращает случайную шутку из перемешанного контейнера.
    """
    shuffle_bag = update_jokes()
    return shuffle_bag.pick()


@tool(return_direct=True)
def get_random_joke(**kwargs) -> str:
    """
    Call this tool whenever the user asks for a joke, anecdote, or humor.
    Use this for keywords: пошути, анекдот, расскажи смешное.
    """
    return get_joke()