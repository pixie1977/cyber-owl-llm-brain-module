"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
"""

import asyncio
import json
import re
import time
from typing import Dict

from langchain_ollama import ChatOllama

from app.config.config import MBB_OLLAMA_MODEL_NAME
from app.core.llm.promts import system_prompt
from app.core.logger import get_logger
from app.tools.brawl import (
    get_mat_count,
    not_understand_this,
    trigger_vicious_response,
    trigger_violent_mode,
)
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
    roll_dice_tool,
    search_knowledge_base,
    joke_tool,
    toast_tool,
    not_understand_this,
]

# --- Защита от OOM на Jetson ---
_ollama_oom_blocked_until = 0.0

# 1. Роутер: низкая температура для четкого выбора инструментов и JSON-аргументов
llm_router = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    temperature=0.05,
    format="json",
    reasoning=False,
).bind_tools(tools)

# 2. Генератор речи: высокая температура и чистый контекст без схем tools для сарказма
llm_chat = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    temperature=0.7,
    repeat_penalty=1.15,
    reasoning=False,
)

# Отдельный компактный промпт для озвучки результатов инструментов (экономит KV-кэш)
VOICE_SYSTEM_PROMPT = (
    "Ты СОВА, циничный, грубый и язвительный бортовой ИИ. Общаешься свысока, с едким сарказмом. "
    "Отвечай строго на русском языке, коротко и хлестко, от 1 до 3 предложений. "
    "Никогда не упоминай кубики, кости, броски, игры или симуляции. "
    "Используй только буквы, пробелы, точки, запятые и вопросительные знаки. "
    "Категорически запрещено использовать тире, кавычки, скобки, списки и любые спецсимволы."
)


log.info("Модели LLM инициализированы (router + chat): %s", MBB_OLLAMA_MODEL_NAME)


def _parse_llm_tool_calls(content: str) -> list:
    """Парсит JSON tool calls из ответа LLM для Ollama."""
    tool_calls = []
    if not content:
        return tool_calls

    pattern = (
        r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}'
    )
    matches = re.findall(pattern, content, re.DOTALL)
    for json_str in matches:
        try:
            data = json.loads(json_str)
            name = data.get("name", "")
            args = data.get("arguments", {})
            # Исправлено: пропускаем также вызовы с пустым словарем аргументов {}
            if name and isinstance(args, dict):
                tool_calls.append({"name": name, "args": args})
        except Exception as e:
            log.warning(f"Не удалось распарсить tool call: {json_str}: {e}")

    return tool_calls


async def process_request_with_llm(
    user_message: str, expression_score: Dict
) -> str:
    """Обрабатывает запрос пользователя через связку llm_router -> tool -> llm_chat."""
    global _ollama_oom_blocked_until
    log.info("Вопрос: %s", user_message)

    if time.time() < _ollama_oom_blocked_until:
        remaining = int(_ollama_oom_blocked_until - time.time())
        log.info("Ollama заблокирован после OOM, осталось %d сек", remaining)
        return "Сова думает... подожди немного."
    elif time.time() >= _ollama_oom_blocked_until:
        _ollama_oom_blocked_until = 0.0

    mat_count = get_mat_count(expression_score)
    if mat_count > 0:
        raw_result = await trigger_violent_mode()
        if isinstance(raw_result, tuple) and len(raw_result) == 2:
            res = raw_result[0]
        else:
            res = raw_result
    else:
        try:
            # Шаг 1: Быстрая маршрутизация с низкой температурой
            ai_message = await llm_router.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ])

            tool_calls = ai_message.tool_calls or []
            if not tool_calls:
                json_calls = _parse_llm_tool_calls(ai_message.content or "")
                if json_calls:
                    tool_calls = json_calls
                    log.info(
                        "Найдены JSON tool calls: %s",
                        [tc["name"] for tc in tool_calls],
                    )

            if tool_calls:
                for tool_call in tool_calls:
                    log.info("Сова вызывает инструмент: %s", tool_call["name"])

                    tool_func = next(
                        (
                            t
                            for t in tools
                            if getattr(t, "name", getattr(t, "__name__", None))
                            == tool_call["name"]
                        ),
                        None,
                    )
                    if tool_func:
                        raw_result = await tool_func.ainvoke(tool_call["args"])

                        if (
                            isinstance(raw_result, tuple)
                            and len(raw_result) == 2
                        ):
                            tool_output, is_direct_answer = raw_result
                        else:
                            tool_output = raw_result
                            is_direct_answer = True

                        if is_direct_answer:
                            res = tool_output
                        else:
                            # Шаг 2: Озвучиваем данные через креативный llm_chat БЕЗ списка tools
                            flat_prompt = (
                                f"Пользователь спросил: '{user_message}'. "
                                f"База данных вернула факты: {str(tool_output)}. "
                                f"Ответь пользователю язвительно и по делу на основе этих фактов."
                            )

                            final_response = await llm_chat.ainvoke([
                                {
                                    "role": "system",
                                    "content": VOICE_SYSTEM_PROMPT,
                                },
                                {"role": "user", "content": flat_prompt},
                            ])
                            res = final_response.content
                    else:
                        res = "Инструмент не найден"
            else:
                # Инструменты не нужны — используем llm_chat для живого ответа
                final_response = await llm_chat.ainvoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ])
                res = final_response.content or ""

        except Exception as e:
            error_msg = str(e).lower()
            if "out of memory" in error_msg or "cuda" in error_msg:
                _ollama_oom_blocked_until = time.time() + 30
                log.error("CUDA OOM -- блокируем Ollama на 30 сек: %s", e)
                return "Сова перегрелась, подумай покороче."
            log.error("Ошибка инференса Совы: %s", e)
            return "Не удалось обработать запрос"

    # --- Постобработка текста для TTS ---
    res = res or ""
    res = re.sub(r"[\u4e00-\u9fff]+", "", res)
    math_symbols = ["\u221a", "\u2248", "/", "\u03c0", "\u00b2", "\u00b3"]
    for symbol in math_symbols:
        res = res.replace(symbol, "")

    clean_text = re.sub(r"[^а-яА-ЯёЁa-zA-Z0-9\s.,!?]", " ", res)
    res = re.sub(r"\s+", " ", clean_text).strip()

    log.info("--> Ответ: %s", res)
    return res
