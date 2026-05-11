"""
Утилиты для преобразования чисел в текст на русском языке.
"""
import re

from app.core.logger import get_logger
from num2words import num2words

log = get_logger(__name__)

import re


def clean_math_text(text: str) -> str:
    # Удаляем " целых ноль десятых", " целых ноль сотых" и т.д.
    # Регулярка ищет паттерн "целых ноль ..." до конца строки или знака препинания
    text = re.sub(r"\sцелых\sноль\s(десятых|сотых|тысячных)", "", text)

    # Дополнительно: если num2words выдает "пять целых ноль десятых",
    # останется просто "пять"
    return text.strip()


# Пример использования:
# raw_text = "десять целых ноль десятых"
# result = clean_math_text(raw_text) # Выдаст: "десять"


def textify_result(result_str: str) -> str:
    # 1. Извлекаем только конечное число из строки 'Result: 1/2 ~ 0.5000'
    # Ищем число после тильды или просто последнее число
    match = re.findall(r"[-+]?\d*\.\d+|\d+", result_str)
    if not match:
        return result_str

    number = float(match[-1])  # Берем последнее найденное число (0.5000)

    # 2. Переводим в текст (на русский)
    # Например: 0.5 -> "ноль целых пять десятых"
    prefix = "м+инус " if number < 0 else ""
    text_result = prefix + num2words(abs(number), lang='ru')
    text_result = clean_math_text(text_result)

    # 3. Расставляем ударения для Silero (базовая логика или просто вернуть текст)
    # Silero обычно неплохо справляется с простыми словами,
    # но можно добавить плюсы в ключевые места вручную через .replace()
    return text_result

def float_to_text_russian(value: str) -> str:
    """
    Преобразует число с плавающей точкой в текстовое представление на русском языке
    с точностью до десятитысячных (4 знака после запятой).

    Примеры:
        3.1415 → "три целых одна тысяча четыреста пятнадцать десятитысячных"
        0.0001 → "одна десятитысячная"
        2.5    → "две целых пять тысяч десятитысячных"

    Args:
        value: Число с плавающей точкой.

    Returns:
        Текстовое представление числа на русском языке.
    """
    # Округляем до 4 знаков после запятой
    try:
        value = round(float(value), 4)
    except ValueError as e:
        log.error(e)
        return "ошибка случилась"

    # Разделяем целую и дробную части
    integer_part = int(abs(value))
    fractional_part = int(round((abs(value) - integer_part) * 10000))  # до 4 знаков

    # Словари для слов
    ones = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
    teens = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
             "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
    tens = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят",
            "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
    hundreds = ["", "сто", "двести", "триста", "четыреста", "пятьсот",
                "шестьсот", "семьсот", "восемьсот", "девятьсот"]
    thousands = ["", "одна тысяча", "две тысячи", "три тысячи", "четыре тысячи",
                 "пять тысяч", "шесть тысяч", "семь тысяч", "восемь тысяч", "девять тысяч"]

    def number_to_words(n: int) -> str:
        if n == 0:
            return ""
        result = []
        t = n // 1000
        h = (n % 1000) // 100
        tn = (n % 100) // 10
        o = n % 10

        if t > 0:
            if t == 1:
                result.append("одна тысяча")
            elif t == 2:
                result.append("две тысячи")
            else:
                result.append(f"{ones[t]} тысяч")

        if h > 0:
            result.append(hundreds[h])

        if tn == 1:
            result.append(teens[o])
        else:
            if tn > 0:
                result.append(tens[tn])
            if o > 0:
                result.append(ones[o])

        return " ".join(result).strip()

    # Преобразуем целую часть
    integer_text = number_to_words(integer_part) or "ноль"

    # Обрабатываем окончания для "целая/целых"
    last_digit = integer_part % 10
    if integer_part % 100 in range(11, 20):
        integer_unit = "целых"
    elif last_digit == 1:
        integer_unit = "целая"
    else:
        integer_unit = "целых"

    # Дробная часть
    if fractional_part == 0:
        return f"{integer_text} {integer_unit}"

    fractional_text = number_to_words(fractional_part) or ""

    # Определяем единицу измерения дробной части
    fractional_last_digit = fractional_part % 10
    fractional_teen = fractional_part % 100
    if fractional_teen in range(11, 20) or fractional_last_digit not in [1, 2]:
        fractional_unit = "десятитысячных"
    elif fractional_last_digit == 1:
        fractional_unit = "десятитысячная"
    else:  # == 2
        fractional_unit = "десятитысячные"

    sign = "минус " if value < 0 else ""
    return f"{sign}{integer_text} {integer_unit} {fractional_text} {fractional_unit}"


if __name__ == "__main__":
    # Тесты для демонстрации работы функции
    test_cases = [
        3.1415,
        0.0001,
        2.5,
        1.0,
        0.0000,
        -1.2345,
        12.3456,
        0.0010,
        9.9999,
        100.0001
    ]

    print("🧪 Тесты функции float_to_text_russian:\n")
    for num in test_cases:
        text = float_to_text_russian(num)
        print(f"{num:>10} → {text}")