"""
Утилиты для обработки текста, извлечения чисел и очистки результатов.
"""

import re
from fuzzywuzzy import fuzz

from app.core.logger import get_logger
from app.utils.time_to_words import time_to_text


log = get_logger(__name__)

def filter_text_math(input_str: str) -> str:
    """
    Извлекает числовое значение из строки, удаляя префиксы и оставляя только число.

    Поддерживает:
      - Извлечение после символа "≈", "~", "=", "равен", "является", "— ", "это"
      - Удаление префиксов: "Результат:", "Ответ:", "Answer:"
      - Извлечение первого числа (целого или дробного, до 4 знаков после запятой)

    Args:
        input_str: Входная строка с результатом.

    Returns:
        Извлечённое число в виде строки или "error", если не найдено.
    """
    res = input_str.strip()

    # Разделители для поиска значения после них
    delimiters = ("≈", "~", "равен", "равно", "=", "является", "— ", "это")
    is_obtained_delimiter = False

    for delimiter in delimiters:
        if delimiter in res:
            is_obtained_delimiter = True
            try:
                res = res.split(delimiter)[-1].strip()
            except Exception:
                res = input_str.strip()  # fallback при ошибке

    if is_obtained_delimiter:
        # Удаляем возможные префиксы
        res = re.sub(
            r"^[Рр]езультат[:\s]*|[Оо]твет[:\s]*|[Aa]nswer[:\s]*",
            "",
            res
        ).strip()

        # Извлекаем первое числовое значение (включая отрицательные и дробные)
        # Поддержка до 4 знаков после запятой
        match = re.search(r"-?\d+\.?\d{0,4}", res)
        if match:
            number_str = match.group(0)
            # Убедимся, что не захватили лишнее (например, 5 цифр)
            if "." in number_str:
                parts = number_str.split(".")
                if len(parts) == 2 and len(parts[1]) > 4:
                    number_str = f"{parts[0]}.{parts[1][:4]}"
            res = number_str
        else:
            res = "error"

    return res


def process_time_answers(text: str) -> str:
    """
    Ищет время в формате HH:MM и преобразует его в текстовое описание.

    Args:
        text: Входной текст с временем.

    Returns:
        Текстовое представление времени или None, если не найдено.
    """
    match = re.search(r"\b([01]?[0-9]|2[0-3]):([0-5][0-9])\b", text)
    if match:
        hour, minute = match.groups()
        hour = f"{int(hour):02d}"
        minute = f"{int(minute):02d}"
        return time_to_text(f"{hour}:{minute}")
    return None


def wrap_answer_with_ssml(msg: str) -> dict:
    """
    Оборачивает текстовое сообщение в SSML-разметку с низким тоном.

    Args:
        msg: Текстовое сообщение.

    Returns:
        Словарь с ключом 'text' и SSML-строкой.
    """
    rs_ssml_text = (
        "<speak>\n"
        "  <prosody pitch=\"low\">\n"
        f"  {msg}\n"
        "  </prosody>\n"
        "</speak>"
    )
    return rs_ssml_text


def fuzzy_find_fw(keyword: str,
                  phrase: str,
                  threshold: int = 80):
    """
    Поиск приблизительных вхождений keyword в phrase с помощью fuzzywuzzy.
    threshold – минимальный процент сходства (0–100), по умолчанию 80 %.
    Возвращает список кортежей (позиция, фрагмент, score).
    """
    kw = keyword.lower()
    text = phrase.lower()
    k = len(kw)
    hits = []

    if k == 0 or k > len(text):
        return hits

    for i in range(len(text) - k + 1):
        window = text[i:i + k]
        score = fuzz.ratio(kw, window)  # 100 – полное совпадение
        if score >= threshold:
            hits.append((i,
                         phrase[i:i + k],  # оригинальный регистр
                         score))
    return hits

def find_and_crop_by_keywords(key_words: list, text: str, threshold: int = 60) -> str:
    for key_word in key_words:
        res = fuzzy_find_fw(key_word, text.lower(), threshold=threshold)
        if res:
            for pos, frag, sc in res:
                log.debug(f'  "{frag}" (позиция {pos}, сходство {sc}%)')
                words = re.findall(r'[а-яё]+', text)
                cropped_words = words[pos+1:]
                cropped_text_local = ' '.join(cropped_words)
                return cropped_text_local

    log.info(f'Совпадений ключевых слов не найдено. Запрос не рассматривается. Запрос:{text}')
    return ""