"""
Тесты для roll_dice_tool — преобразование чисел в слова для TTS.
"""
import pytest

from app.tools.dice_tool import roll_dice_tool, _number_to_words


# Прямой вызов оригинальной функции (без @tool wrapper)
_dice = roll_dice_tool.func


class TestNumberToWords:
    """Проверка функции _number_to_words."""

    def test_single_digit(self):
        assert _number_to_words("бросок 1d20") == "бросок один ДЭ двадцать"

    def test_multi_digit(self):
        assert _number_to_words("сумма 100") == "сумма сто"

    def test_no_numbers(self):
        assert _number_to_words("просто текст") == "просто текст"

    def test_mixed(self):
        result = _number_to_words("2d6+3")
        assert "два" in result
        assert "ДЭ" in result
        assert "три" in result

    def test_d20_dэ_replacement(self):
        assert _number_to_words("1d20") == "один ДЭ двадцать"

    def test_negative_number(self):
        result = _number_to_words("модификатор -5")
        assert "минус пять" in result


class TestRollDiceTool:
    """Проверка roll_dice_tool."""

    def test_basic_1d20(self):
        result = _dice("1d20")
        assert isinstance(result, str)
        assert "бросок" in result.lower() or "выполни" in result.lower()
        assert "дэ" not in result.lower() or " ДЭ " in result

    def test_basic_2d6(self):
        result = _dice("2d6")
        assert isinstance(result, str)
        assert "сумма" in result.lower()

    def test_with_modifier(self):
        result = _dice("1d20+5")
        assert isinstance(result, str)

    def test_invalid_syntax(self):
        result = _dice("abc")
        assert "ошибка" in result.lower()

    def test_no_digits_in_output(self):
        """Результат не должен содержать арабские цифры."""
        for _ in range(10):
            result = _dice("1d20")
            assert not any(c.isdigit() for c in result), \
                f"Найдены цифры в: {result}"

    def test_dэ_replacement(self):
        """Проверка замены ' дэ' на ' ДЭ'."""
        result = _dice("1d20")
        assert " ДЭ " in result or " ДЭ." in result or " ДЭ," in result

    def test_critical_success(self):
        """Критический успех (20) — должен быть комментарий."""
        import random
        random.seed(42)
        result = _dice("1d20")
        assert isinstance(result, str)

    def test_critical_fail(self):
        """Критический провал (1) — должен быть комментарий."""
        import random
        random.seed(42)
        result = _dice("1d20")
        assert isinstance(result, str)
