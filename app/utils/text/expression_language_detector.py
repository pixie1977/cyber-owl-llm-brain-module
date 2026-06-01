# python
import re
from collections import defaultdict
from typing import Dict, List, Pattern

import pymorphy2
from sqlalchemy.sql.coercions import expect_col_expression_collection

from app.utils.utils import Utils


class RussianExpressionLanguageDetector:
    """
    Определяет наличие ненормативной русскоязычной лексики
    и вычисляет «уровень экспрессии» текста.

    1. Ищет ненормативную лексику (мат), блатную феню, профессиональный жаргон (можно добавить свои категории).
    2. Возвращает:
       • количество найденных слов по каждой категории;
       • общую числовую «оценку экспрессии»;
       • словесный уровень экспрессии: `low / medium / high`.

    По умолчанию используется простая система весов:
    `мат` — 3 балла, `блатная феня` — 2 балла, `проф. жаргон` — 1 балл.
    Алгоритм легко расширить — достаточно добавить/поправить регулярные выражения.

    """

    # -------------------  Конфигурация по умолчанию  -------------------
    _DEFAULT_PATTERNS = {
        "mat": [
            # корень + возможные суффиксы/приставки
            r"\bх[уy]й[а-я]*",  # хуй, хуёвый, etc.
            r"\bп[ие]зд[а-я]*",  # пизда, пиздеть, etc.
            r"\b([её])б[а-я]*",  # ебать, ёбнутый, etc.
            r"\b(зло[её])б[а-я]*",  # злое...
            r"\bбля[тд]?[а-я]*",  # бля, блядь
            r"\bсука\b", r"\bсучк[аоие]",  # сука во всех падежах
            r"\bтвар?[а-я]*",  # тварь
            r"\bманда?[а-я]*",  # манда*
        ],
        "blat": [
            r"\bмусор(?:[а-я]*)\b",  # мент/полиция в феней
            r"\bшерсть\b",
            r"\bшконк[аеуы]\b",
            r"\bфраер(?:[а-я]*)\b",
            r"\bбеспредел\b",
            r"\bхавать\b",
        ],
        "pro_slang": [
            r"\bдеплой[а-я]*\b",
            r"\bрелиз[а-я]*\b",
            r"\bбаг[а-я]*\b",
            r"\bфич[а-я]*\b",
            r"\bкоммит[а-я]*\b",
            r"\bпрод\b",
        ],
    }

    _DEFAULT_WEIGHTS = {"mat": 3, "blat": 2, "pro_slang": 1}

    _log = Utils.create_logger(__name__)

    def __init__(
            self,
            patterns: Dict[str, List[str]] = None,
            weights: Dict[str, int] = None,
            levels=((0, 3, "low"), (3, 10, "medium"), (10, float("inf"), "high")),
    ):
        # Инициализируем морфологический анализатор

        self.morph = pymorphy2.MorphAnalyzer()

        self.patterns: Dict[str, List[Pattern]] = {
            cat: [re.compile(pat, re.I | re.U) for pat in pats]
            for cat, pats in (patterns or self._DEFAULT_PATTERNS).items()
        }
        self.weights = weights or self._DEFAULT_WEIGHTS
        self.levels = levels

    def analyze(self, text: str) -> Dict:
        """
        Улучшенный анализ: сочетает регулярные выражения и морфологический разбор.
        """
        normalized = self._normalize(text)
        # Извлекаем только слова (кириллица, латиница и дефис)
        words = re.findall(r'[а-яёa-z-]+', normalized)

        counts = defaultdict(int)
        matches = defaultdict(list)

        for word in words:
            # Получаем лемму (начальную форму) слова
            # Например: "багами" -> "баг"
            lemma = self.morph.parse(word)[0].normal_form

            word_found_in_category = False

            for category, regex_list in self.patterns.items():
                for regex in regex_list:
                    # Проверяем и исходное слово, и его лемму
                    if regex.search(word) or regex.search(lemma):
                        counts[category] += 1
                        matches[category].append(word)
                        word_found_in_category = True
                        break  # Слово соотнесено с категорией, идем к следующему слову

                if word_found_in_category:
                    break

        # Считаем суммарный балл с учетом весов
        total_score = sum(
            self.weights.get(cat, 1) * cnt for cat, cnt in counts.items()
        )

        # Определяем словесный уровень экспрессии через генератор
        level_label = "low"  # Значение по умолчанию
        for low, high, label in self.levels:
            if low <= total_score < high:
                level_label = label
                break

        return {
            "counts": dict(counts),
            "total_score": total_score,
            "expressivity_level": level_label,
            "matches": dict(matches),
        }

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Упрощённая нормализация:
        1) lower-case,
        2) замена 'ё'->'е'.
        Этого достаточно для грубого мат-детектора.
        """
        return text.lower().replace("ё", "е")


# -------------------  Пример использования  -------------------
if __name__ == "__main__":
    from pprint import pprint

    expression_detector = RussianExpressionLanguageDetector()

    sample = """
        Ты чего, блядь, опять баг в прод выкатил?
        Мусора уже весь деплой обнесли, ха!
        Это ж полнейший беспредел.
        Понаберут всякую шерсть в разрабов - а ты страдай.
    """

    result = expression_detector.analyze(sample)
    pprint(result)
'''
Как донастраивать
-----------------
1. Добавить/исправить категории: передайте свой `patterns` при создании экземпляра.  
2. Задать другие веса: аргумент `weights`.  
3. Изменить пороги уровней экспрессии: поменяйте `levels`.  
4. Для более точного распознавания можно подключить `pymorphy2` (лемматизация) и/или модуль `rure` (Regex PCRE2) для очень большого списка слов; интерфейс класса менять не придётся.
'''
