"""Модуль для генерации саркастичных и агрессивных ответов.

Использует шаблоны и случайные слова из ShuffleBag («интеллектуальная хамоватость»).
"""

from langchain_core.tools import tool

from app.tools.brawl_data.brawl_templates import brawl_templates_shuffle
from app.tools.brawl_data.brawl_words import agressive_words_shuffle
from app.core.logic.shuffle_bag import ShuffleBag

not_understand_shuffle = ShuffleBag([
    "Ни хера не поняла, но очень интересно!",
    "Ты втираешь мне какую-то дичь!",
    "Не понимаю тебя",
    "Че за бред?",
    "Свали и потеряйся!",
    "Че ты бур+овишь?",
    "НЕ ПОНИМАЮ ТВОЙ БРЭД!",
    "Херня. Мне неинтересно!",
    "Меньше звуков, больше дистанции",
    "Ты мне надо+ело",
])


class BrawlerSova:
    """Генератор язвительных высказываний."""

    def __init__(self, shuffle_bag_words) -> None:
        """Инициализация боец-совы.

        :param shuffle_bag_words: Экземпляр ShuffleBag со словами для вставки
            в шаблоны.
        """
        self.shuffle_bag_words = shuffle_bag_words

    def generate_insult(self) -> str:
        """Генерирует оскорбление по шаблону, подставляя три случайных слова.

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
    """Извлекает количество матов из словаря оценки высказывания.

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
def not_understand_this(**kwargs) -> tuple[str, bool]:
    """Инструмент для генерации жёсткого и саркастичного ответа.

    Вызывай при вопросе, который НЕ ПОНИМАЕШЬ.

    :param kwargs: Игнорируемые параметры.
    :return: Кортеж из текста ответа и флага успешности.
    """
    return not_understand_shuffle.pick(), True


@tool
def trigger_vicious_response(**kwargs) -> tuple[str, bool]:
    """Инструмент для генерации жёсткого и саркастичного ответа на хамство.

    Вызывай при ЛЮБОМ намеке на нелогичные вопросы или хамство.

    :param kwargs: Игнорируемые параметры.
    :return: Кортеж из текста ответа и флага успешности.
    """
    return brawler.generate_insult(), True


@tool
def trigger_violent_mode() -> tuple[str, bool]:
    """Инструмент для генерации абсолютно нецензурного контента.

    Вызывается, когда обнаружено матерное выражение в текстовом сообщении.

    :return: Кортеж из текста ответа и флага успешности.
    """
    return "ответом будет матерная брань", True
