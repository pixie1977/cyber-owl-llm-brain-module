"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
"""

import asyncio
import json
import re
import time
from typing import Dict

from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama

from app.config.config import MBB_OLLAMA_MODEL_NAME
from app.core.logger import get_logger
from app.core.llm.promts import system_prompt
from app.tools.brawl import get_mat_count, trigger_vicious_response, trigger_violent_mode, not_understand_this
from app.tools.dice_tool import roll_dice_tool
from app.tools.jokes import joke_tool
from app.tools.math import math_tool
from app.tools.qdrant import search_knowledge_base
from app.tools.time import time_tool
from app.tools.toast import toast_tool

# --- Настройка логирования ---
log = get_logger(__name__)

# Список инструментов
tools = [
    trigger_vicious_response,
    trigger_violent_mode,
    time_tool,
    math_tool,
    search_knowledge_base,
    joke_tool,
    toast_tool,
    not_understand_this,
    roll_dice_tool
]

# --- Защита от OOM на Jetson ---
_ollama_oom_blocked_until = 0.0

# --- Настройка модели Ollama ---
llm = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    reasoning=False,  # Отключает thinking mode в свежих версиях langchain-ollama
).bind_tools(tools)

log.info("Модель LLM инициализирована: %s", llm.model)
log.info("Системный промпт и шаблон загружены.")
log.info("num_ctx=1024 (оптимизировано для Jetson с ограниченной VRAM)")


def _parse_llm_tool_calls(content: str) -> list:
    """Парсит JSON tool calls из ответа LLM для Ollama.
    
    Ollama возвращает инструмент как JSON в content:
    {"name": "roll_dice_tool", "arguments": {"dice_expression": "1d20"}}
    """
    tool_calls = []
    if not content:
        return tool_calls

    # Ищем JSON-объект с полями name и arguments
    pattern = r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}'
    matches = re.findall(pattern, content, re.DOTALL)
    for json_str in matches:
        try:
            data = json.loads(json_str)
            name = data.get("name", "")
            args = data.get("arguments", {})
            if name and args:
                tool_calls.append({"name": name, "args": args})
        except Exception as e:
            log.warning(f"Не удалось распарсить tool call: {json_str}: {e}")

    return tool_calls


async def process_request_with_llm(user_message: str, expression_score: Dict) -> str:
    """Обрабатывает запрос пользователя напрямую через нативный Tool Calling Ollama."""
    global _ollama_oom_blocked_until
    log.info("Вопрос: %s", user_message)

    # Проверяем, не заблокирован ли Ollama после OOM
    if time.time() < _ollama_oom_blocked_until:
        remaining = int(_ollama_oom_blocked_until - time.time())
        log.info("Ollama заблокирован после OOM, осталось %d сек", remaining)
        return "Сова думает... подожди немного."
    elif time.time() >= _ollama_oom_blocked_until:
        _ollama_oom_blocked_until = 0  # разблокируем

    mat_count = get_mat_count(expression_score)
    if mat_count > 0:
        res = trigger_violent_mode()
    else:
        try:
            # 1. Быстрый запрос к Ollama (промпт уже в кэше GPU!)
            ai_message = await llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ])

            # 2. Проверяем, хочет ли модель вызвать инструмент
            tool_calls = ai_message.tool_calls or []
            if not tool_calls:
                # Ollama может вернуть JSON tool call в content
                json_calls = _parse_llm_tool_calls(ai_message.content or "")
                if json_calls:
                    tool_calls = json_calls
                    log.info("Найдены JSON tool calls: %s", [tc["name"] for tc in tool_calls])

            if tool_calls:
                for tool_call in tool_calls:
                    log.info("Сова вызывает инструмент: %s", tool_call["name"])

                    tool_func = next(
                        (t for t in tools if getattr(t, "name", getattr(t, "__name__", None)) == tool_call["name"]), None)
                    if tool_func:
                        # Выполняем инструмент локально
                        raw_result = await tool_func.ainvoke(tool_call["args"])

                        # Инструменты возвращают (str, bool) или просто str
                        if isinstance(raw_result, tuple) and len(raw_result) == 2:
                            tool_output, is_direct_answer = raw_result
                        else:
                            tool_output = raw_result
                            is_direct_answer = True

                        if is_direct_answer:
                            res = tool_output
                        else:
                            # Плоский запрос вместо раздувания графа -- экономит VRAM
                            flat_prompt = (
                                f"Пользователь спросил: '{user_message}'. "
                                f"Системный инструмент вернул данные: {str(tool_output)}. "
                                f"Сформируй финальный краткий ответ для пользователя на основе этих данных."
                            )

                            final_response = await llm.ainvoke([
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": flat_prompt}
                            ])
                            res = final_response.content

                    else:
                        res = "Инструмент не найден"
            else:
                # Если инструменты не нужны, берем прямой ответ модели
                res = ai_message.content

        except Exception as e:
            error_msg = str(e).lower()
            if "out of memory" in error_msg or "cuda" in error_msg:
                # OOM -- блокируем Ollama на 30 сек, даём освободить память
                _ollama_oom_blocked_until = time.time() + 30
                log.error("CUDA OOM -- блокируем Ollama на 30 сек: %s", e)
                return "Сова перегрелась, подумай покороче."
            log.error("Ошибка инференса Совы: %s", e)
            return "Не удалось обработать запрос"

    # --- Постобработка текста для TTS ---
    res = re.sub(r'[\u4e00-\u9fff]+', '', res)  # убираем иероглифы
    math_symbols = ['\u221a', '\u2248', '/', '\u03c0', '\u00b2', '\u00b3']
    for symbol in math_symbols:
        res = res.replace(symbol, '')

    # Чистим от случайных спецсимволов (XML-теги, маркеры и т.п.)
    clean_text = re.sub(r"[^а-яА-ЯёЁa-zA-Z0-9\s.,!?]", " ", res)
    res = re.sub(r"\s+", " ", clean_text).strip()

    log.info("--> Ответ: %s", res)
    return res


# --- Пример использования ---
async def main():
    """Запуск тестовых запросов."""
    questions = [
        "тост!",
        "скажи тост!!!",
        "скажи тост за Макса",
        "скажи тост за команду",
        "скажи тост, бля",
        "бля",
        "мудрый олень пиявка",
        "почему трава зеленая?",
        "ты невесомый дебил?",
        "пошути",
        "косинус пи пополам",
        "косинус девяносто градусов",
        "пять плюс три в квадрате",
        "Который сейчас час?",
        "Расскажи о Париже",
        "Чему равно 15 * 4 + 10?",
        "Посчитай (5 + 3) ** 2",
        "Посчитай три плюс два в скобках и возвести в квадрат",
        "синус нуля",
        "синус тридцати градусов",
        "синус сорока пяти градусов",
        "что такое магнетар",
        "Что такое гипотеза Эверетта?",
        "Орфей и Эвридика",
    ]
    for q in questions:
        await process_request_with_llm(q, None)


if __name__ == "__main__":
    asyncio.run(main())
