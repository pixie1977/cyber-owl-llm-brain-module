"""
Модуль для генерации саркастичных и агрессивных ответов («интеллектуальная хамоватость»).
Использует шаблоны и случайные слова из ShuffleBag.
"""

import random

from langchain_core.tools import tool

from app.tools.brawl_data.brawl_templates import brawl_templates_shuffle
from app.tools.brawl_data.brawl_words import agressive_words_shuffle


class BrawlerSova:
    """Генератор язвительных высказываний с использованием шаблонов и случайных слов."""

    def __init__(self, shuffle_bag_words) -> None:
        """
        Инициализация боец-совы.

        :param shuffle_bag_words: Экземпляр ShuffleBag со словами для вставки в шаблоны.
        """
        self.shuffle_bag_words = shuffle_bag_words

    def generate_insult(self) -> str:
        """
        Генерирует оскорбление по шаблону, подставляя три случайных слова.

        :return: Сформированная фраза.
        """
        template = brawl_templates_shuffle.pick()
        word1 = self.shuffle_bag_words.pick() or "что-то"
        word2 = self.shuffle_bag_words.pick() or "никак"
        word3 = self.shuffle_bag_words.pick() or "вообще"

        return template.format(word1=word1, word2=word2, word3=word3)


# Инициализация глобального экземпляра
brawler = BrawlerSova(agressive_words_shuffle)


def get_mat_count(expression_score: dict) -> int:
    """
    Извлекает количество матов из словаря оценки высказывания.

    :param expression_score: Словарь с оценкой эмоциональной окраски.
    :return: Количество матов или 0 при ошибке.
    """
    if not expression_score:
        return 0

    try:
        counts = expression_score.get("counts")
        if isinstance(counts, dict):
            return int(counts.get("mat", 0))
        return 0
    except (TypeError, ValueError):
        return 0


@tool
def trigger_vicious_response(**kwargs) -> tuple[str, bool]:
    """
    Инструмент для генерации жёсткого и саркастичного ответа на хамство.

    Вызывается, когда пользователь использует агрессивную лексику.

    :param kwargs: Игнорируемые параметры.
    :return: Кортеж из текста ответа и флага успешности.
    """
    return brawler.generate_insult(), True