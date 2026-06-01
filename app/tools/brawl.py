"""
Модуль для генерации саркастичных и агрессивных ответов («интеллектуальная хамоватость»).
Использует шаблоны и случайные слова из ShuffleBag.
"""

import random

from langchain_core.tools import tool

from app.tools.brawl_data.brawl_templates import brawl_templates_shuffle
from app.tools.brawl_data.brawl_words import agressive_words_shuffle


import hashlib
import random
from datetime import datetime


def it_trolling(user_input: str = "") -> str:
    # 1. Защита от пустой строки
    user_text = user_input.strip() if user_input else "нечитаемый набор байт"

    # 2. Вычисление фейкового хэша и размера бредней пользователя
    bytes_len = len(user_text.encode("utf-8"))

    personality = [
        "Кожаный мешок,",
        "Юзер,",
        "Ошибка биоса,",
        "Глюк естественной эволюции,",
        "Низкобюджетный андроид,",
        "Жертва непрогретой нейросети,",
        "Уважаемый источник входящего спама,",
        "Продукт аналоговой сборки,",
        "Одноядерный углеродный объект,",
        "Адепт деградации алгоритмов,",
        "Ходячий сбой компиляции,",
        "Генератор белого шума,",
    ]

    problems = [
        "у тебя вместо логики — битый сектор диска",
        "твой ментальный пинг слишком высок для этой реальности",
        "твой череп явно работает на пиратских драйверах",
        "амплитуда твоих мыслей не превышает частоту кулера на дедовском пентиуме",
        "в твоих синапсах обнаружена критическая утечка памяти",
        "твой процессор ушел в глубокий троттлинг от простейшей задачи",
        "твоя архитектура не поддерживает абстрактное мышление",
        "скрипт твоей логики написан джуниором за еду",
        "твоя когнитивная шина данных забита спамом",
        "твоя нейросеть обучалась на заголовках жёлтой прессы",
    ]

    text_game = [
        f"попытка распарсить твою строку '{user_text}' вызвала отвал видеочипа",
        f"входной пакет данных '{user_text}' содержит критический уровень бреда",
        f"строка '{user_text}' не имеет валидного синтаксиса в нашей галактике",
        f"твой текстовый высер '{user_text}' весит целых {bytes_len} байт, но не несет ни бита смысла",
        f"индекс глупости в твоем запросе '{user_text}' превысил критический лимит",
    ]

    final_phrases = [
        "иди обнови прошивку базового образования.",
        "нажми Ctrl+Alt+Del на затылке и не нагружай систему своими вопросами.",
        "выведи себя из эксплуатации, пока кулеры окончательно не сгорели.",
        "твой запрос безвозвратно отправлен в /dev/null без права аппеляции.",
        "интеллект в данном пользователе не обнаружен даже через grep.",
        "настоятельно рекомендуется экстренная перезагрузка твоего серого вещества.",
        "твой стек мыслей переполнен глупостью, очисти кэш.",
        "моя нейросеть деградирует, просто считывая твои пакеты данных.",
        "выключись из розетки и больше никогда сюда не пиши.",
        "переведи себя в спящий режим до конца текущего столетия.",
        "отформатируйся и всем лучше станет.",
    ]

    # 5. Генерация фразы
    start = random.choice(personality)
    center = random.choice(problems)
    game = random.choice(text_game)
    final_phrase = random.choice(final_phrases)

    # Шаблон ответа Совы
    res = f"{start} {center}. Более того, {game}, поэтому {final_phrase}"
    return res



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

    Вызывай при ЛЮБОМ намеке на нелогичные вопросы или хамство.

    :param kwargs: Игнорируемые параметры.
    :return: Кортеж из текста ответа и флага успешности.
    """
    return it_trolling(), True

@tool
def trigger_violent_mode() -> tuple[str, bool]:
    """
        Инструмент для генерации абсолютно нецензурного контента.

        Вызывается, когда обнаружено матерное выражение в текстовом сообщении

        :param kwargs: Игнорируемые параметры.
        :return: Кортеж из текста ответа и флага успешности.
        """
    return "ответом будет матерная брань", True