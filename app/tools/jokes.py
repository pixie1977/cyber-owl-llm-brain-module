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

    :return: Экземпляр ShuffleBag с шутками.
    """
    logger.info("Загружаем шутки...")
    jokes_list = []

    try:
        with open(JOKES_FILE_PATH, "r", encoding="utf-8") as file:
            for line in file:
                cleaned_line = line.strip()
                if cleaned_line:  # Игнорируем пустые строки
                    jokes_list.append(cleaned_line)
    except FileNotFoundError:
        logger.error("Файл с шутками не найден: %s", JOKES_FILE_PATH)
        return ShuffleBag([])
    except Exception as e:
        logger.error("Ошибка при чтении файла шуток: %s", e)
        return ShuffleBag([])

    logger.info("Загружено %d шуток.", len(jokes_list))
    return ShuffleBag(jokes_list)


def update_jokes() -> ShuffleBag:
    """
    Инициализирует или возвращает существующий экземпляр ShuffleBag с шутками.

    :return: Экземпляр ShuffleBag.
    """
    global JOKES_SHUFFLE
    if JOKES_SHUFFLE is None:
        JOKES_SHUFFLE = load_jokes()
    return JOKES_SHUFFLE


def get_joke() -> str:
    """
    Возвращает случайную шутку из перемешанного контейнера.

    :return: Случайная шутка или сообщение об отсутствии шуток.
    """
    shuffle_bag = update_jokes()
    joke = shuffle_bag.pick()
    return joke if joke else "Шутки закончились! Попробуйте позже."


@tool
def get_random_joke(**kwargs) -> tuple[str, bool]:
    """
    Возвращает случайную шутку. Вызывается, когда пользователь просит пошутить.

    Используется при запросах: пошути, анекдот, расскажи смешное и т.п.

    :param kwargs: Игнорируемые именованные аргументы.
    :return: Кортеж из шутки и флага успешности.
    """
    return get_joke(), True