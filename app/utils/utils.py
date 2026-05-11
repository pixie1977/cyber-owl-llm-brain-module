"""
Модуль утилит для работы с логами, временем, словами и fuzzy-поиском.
"""

import datetime
import json
import locale
import logging
import os
import sys
from typing import List, Tuple, Set

from fuzzywuzzy import fuzz

from app.utils.text.insult_phrase_generator import generate_insult_phrase
from app.utils.text.time_to_words import time_to_text


# Настройка логгера
logging.basicConfig()


class Utils:
    """Класс утилит с набором статических методов."""

    @staticmethod
    def get_root_dir() -> str:
        """Возвращает абсолютный путь к директории модуля."""
        return os.path.abspath(os.path.dirname(__file__))

    @staticmethod
    def create_logger(name: str) -> logging.Logger:
        """
        Создаёт и настраивает логгер.

        Args:
            name (str): Имя логгера.

        Returns:
            logging.Logger: Настроенный логгер.
        """
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

        # Обработчик для stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(formatter)
        log.addHandler(stdout_handler)

        # Обработчик для файла
        file_path = os.path.join(Utils.get_root_dir(), 'sowa_logs.log')
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

        return log

    @staticmethod
    def bad_words_load(file_path: str) -> Set[str]:
        """
        Загружает список плохих слов из файла.

        Args:
            file_path (str): Путь к файлу.

        Returns:
            set: Множество слов.
        """
        print('Загружаем справочник слов...')
        words = []
        with open(file_path, 'r', encoding='utf-8') as infile:
            for line in infile:
                word = line.strip()
                if word:
                    words.append(word)
        print(f"Загружено {len(words)} слов.")
        return set(words)

    @staticmethod
    def audio_reactions_load(file_path: str) -> List[dict]:
        """
        Загружает список аудио-реакций из JSON-файла.

        Args:
            file_path (str): Путь к JSON-файлу.

        Returns:
            list: Список элементов из поля 'items'.
        """
        print('Загружаем справочник аудио реакций...')
        with open(file_path, 'r', encoding='utf-8') as f_json:
            data = json.load(f_json)
        return data.get('items', [])

    @staticmethod
    def compare_lists(input_words: List[str], expected: List[str]) -> bool:
        """
        Проверяет пересечение двух списков.

        Args:
            input_words (list): Первый список слов.
            expected (list): Второй список слов.

        Returns:
            bool: True, если есть общие слова.
        """
        set_input = set(input_words)
        set_expected = set(expected)
        return bool(set_input.intersection(set_expected))

    @staticmethod
    def exclude_words(command: List[str], last_command: List[str]) -> Set[str]:
        """
        Возвращает разницу между двумя списками слов.

        Args:
            command (list): Текущий список слов.
            last_command (list): Предыдущий список слов.

        Returns:
            set: Слова, которые есть в текущем, но нет в предыдущем.
        """
        set_command = set(command)
        set_last = set(last_command)
        return set_command.difference(set_last)

    @staticmethod
    def check_command(command: str, last_commands: List[str]) -> List[str]:
        """
        Проверяет команду: разбивает на слова и исключает повторы.

        Args:
            command (str): Входная команда.
            last_commands (list): Список последних команд.

        Returns:
            list: Новые слова в команде.
        """
        result = []

        if not command or len(command.strip()) <= 1:
            return result

        list_command = command.lower().split()
        list_last_commands = [word.lower() for word in last_commands]
        new_words = Utils.exclude_words(list_command, list_last_commands)

        return list(new_words)

    @staticmethod
    def time_as_words() -> str:
        """
        Возвращает текущее время словами на русском языке.

        Returns:
            str: Время словами.
        """
        try:
            locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        except locale.Error:
            print("Не удалось установить локаль 'ru_RU.UTF-8'. Используется стандартный вывод.")

        return time_to_text(datetime.datetime.now())

    @staticmethod
    def generate_insult_phrase() -> str:
        """
        Генерирует оскорбительную фразу.

        Returns:
            str: Сгенерированная фраза.
        """
        return generate_insult_phrase(3)

    @staticmethod
    def fuzzy_find_fw(
        keyword: str,
        phrase: str,
        threshold: int = 80
    ) -> List[Tuple[int, str, int]]:
        """
        Поиск приблизительного вхождения keyword в phrase с помощью fuzzywuzzy.

        Args:
            keyword (str): Ключевое слово для поиска.
            phrase (str): Фраза, в которой ищем.
            threshold (int): Минимальный порог сходства (0–100). По умолчанию 80.

        Returns:
            list: Список кортежей (позиция, фрагмент, score).
        """
        if not keyword or not phrase:
            return []

        kw = keyword.lower()
        text = phrase.lower()
        k_len = len(kw)
        hits = []

        if k_len > len(text):
            return hits

        for i in range(len(text) - k_len + 1):
            window = text[i:i + k_len]
            score = fuzz.ratio(kw, window)
            if score >= threshold:
                fragment = phrase[i:i + k_len]  # сохраняем оригинальный регистр
                hits.append((i, fragment, score))

        return hits


# Пример использования
if __name__ == '__main__':
    test_phrase = 'Сегодня потрясающая погода, поедем гулять у пагоды?'
    test_keyword = 'пагода'
    results = Utils.fuzzy_find_fw(test_keyword, test_phrase, threshold=70)

    if results:
        print('Найдено (порог 70 %):')
        for pos, frag, score in results:
            print(f'  "{frag}" (позиция {pos}, сходство {score}%)')
    else:
        print('Совпадений не найдено.')