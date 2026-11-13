"""
Тесты для app/core/llm/llm.py — маршрутизация, парсинг, постобработка.
"""
import re

import pytest

from app.core.llm.llm import (
    _number_to_words,
    classify_intent,
    _extract_tool_call,
    _parse_args,
    RE_MODE_CONSULTANT,
    RE_MODE_TOOLS,
)


class TestNumberToWords:
    """Преобразование чисел в словесный вид."""

    def test_simple_integer(self):
        assert _number_to_words("ответ 42") == "ответ сорок два"

    def test_leading_zero(self):
        assert _number_to_words("число 0") == "число ноль"

    def test_no_numbers(self):
        assert _number_to_words("просто текст") == "просто текст"

    def test_multiple_numbers(self):
        result = _number_to_words("1 и 2 и 3")
        assert "один" in result
        assert "два" in result
        assert "три" in result

    def test_negative_number(self):
        result = _number_to_words("минус 5")
        assert "минус пять" in result

    def test_large_number(self):
        result = _number_to_words("1000")
        assert "тысяч" in result

    def test_mixed_letters_and_digits(self):
        # 123abc — regex найдёт "123"
        result = _number_to_words("код 123abc")
        assert "сто двадцать три" in result

    def test_empty_string(self):
        assert _number_to_words("") == ""


class TestClassifyIntent:
    """Классификация намерений (crazy / consultant / tools)."""

    def test_consultant_keywords(self):
        assert classify_intent("что такое магнетар") == "consultant"
        assert classify_intent("расскажи про Париж") == "consultant"
        assert classify_intent("найди информацию о котах") == "consultant"

    def test_tools_keywords(self):
        assert classify_intent("который час") == "tools"
        assert classify_intent("посчитай 2+2") == "tools"
        assert classify_intent("кинь кубик") == "tools"
        assert classify_intent("скажи тост") == "tools"
        assert classify_intent("пошути") == "tools"

    def test_crazy_default(self):
        assert classify_intent("привет, как дела?") == "crazy"
        assert classify_intent("я просто болтаю") == "crazy"
        assert classify_intent("") == "crazy"


class TestParseArgs:
    """Парсинг аргументов инструмента."""

    def test_dict_input(self):
        assert _parse_args({"key": "value"}) == {"key": "value"}

    def test_valid_json_string(self):
        assert _parse_args('{"key": "value"}') == {"key": "value"}

    def test_invalid_json_string(self):
        assert _parse_args("not json") == {}

    def test_none_input(self):
        assert _parse_args(None) == {}

    def test_list_input(self):
        assert _parse_args([1, 2]) == {}


class TestExtractToolCall:
    """Извлечение tool_call из ответа LLM."""

    def test_native_tool_calls(self):
        """Нативные tool_calls (ai_message.tool_calls != None)."""
        mock_msg = type("MockMsg", (), {
            "tool_calls": [{"name": "time_tool", "args": {}}],
            "content": None,
        })()
        result = _extract_tool_call(mock_msg)
        assert result is not None
        assert result["name"] == "time_tool"

    def test_json_in_content(self):
        """JSON tool call внутри content."""
        mock_msg = type("MockMsg", (), {
            "tool_calls": None,
            "content": '{"name": "joke_tool", "arguments": {}}',
        })()
        result = _extract_tool_call(mock_msg)
        assert result is not None
        assert result["name"] == "joke_tool"

    def test_no_tool_call(self):
        """Нет tool calls — возвращает None."""
        mock_msg = type("MockMsg", (), {
            "tool_calls": None,
            "content": "Просто текстовый ответ",
        })()
        assert _extract_tool_call(mock_msg) is None

    def test_no_braces_in_content(self):
        """Нет фигурных скобок — сразу None."""
        mock_msg = type("MockMsg", (), {
            "tool_calls": None,
            "content": None,
        })()
        assert _extract_tool_call(mock_msg) is None


class TestRegexPatterns:
    """Проверка регулярных выражений."""

    def test_consultant_pattern(self):
        assert RE_MODE_CONSULTANT.search("что такое")
        assert RE_MODE_CONSULTANT.search("расскажи про")

    def test_tools_pattern(self):
        assert RE_MODE_TOOLS.search("который час")
        assert RE_MODE_TOOLS.search("посчитай")
        assert RE_MODE_TOOLS.search("кубик")
