"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
Оптимизирован под Jetson Orin NX (16GB) для максимальной скорости и защиты от OOM.
"""

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

log = get_logger(__name__)

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

# Словарь для быстрого поиска инструментов за O(1)
TOOLS_MAP = {
    getattr(t, "name", getattr(t, "__name__", "")): t for t in tools
}

_ollama_oom_blocked_until = 0.0

# Единый инстанс LLM: сохраняет общий KV-кэш для системного промпта и снижает расход RAM
llm_base = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    temperature=0.5,        # Баланс между точностью вызова tools и сарказмом
    repeat_penalty=1.15,
    num_ctx=2048,           # Жесткий лимит контекста спасает от фрагментации памяти и OOM
    num_predict=160,        # Лимит токенов на ответ (3-4 предложения максимум)
    keep_alive="15m",       # Держим модель в памяти GPU, чтобы не тратить время на выгрузку/загрузку
    reasoning=False,
)

# Привязываем инструменты к базовому инстансу (схема кэшируется в префиксе)
llm_agent = llm_base.bind_tools(tools)

VOICE_SYSTEM_PROMPT = (
    "Ты СОВА, циничный, грубый и язвительный бортовой ИИ. Общаешься свысока, с едким сарказмом. "
    "Отвечай строго на русском языке, коротко и хлестко, от 1 до 3 предложений. "
    "Никогда не упоминай кубики, кости, броски, игры или симуляции. "
    "Используй только буквы, пробелы, точки, запятые и вопросительные знаки. "
    "Категорически запрещено использовать тире, кавычки, скобки, списки и любые спецсимволы."
)

# Предкомпилированные регулярки для ускорения постобработки
RE_TOOL_JSON = re.compile(
    r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}',
    re.DOTALL,
)
RE_CHINESE = re.compile(r"[\u4e00-\u9fff]+")
RE_CLEAN_TEXT = re.compile(r"[^а-яА-ЯёЁa-zA-Z0-9\s.,!?]")
RE_SPACES = re.compile(r"\s+")

log.info("Единый LLM-агент инициализирован: %s", MBB_OLLAMA_MODEL_NAME)


def _parse_llm_tool_calls(content: str) -> list:
    """Fallback-парсер JSON tool calls, если модель вернула вызов текстом."""
    if not content or "{" not in content:
        return []

    tool_calls = []
    for json_str in RE_TOOL_JSON.findall(content):
        try:
            data = json.loads(json_str)
            name = data.get("name", "")
            args = data.get("arguments", {})
            if name and isinstance(args, dict):
                tool_calls.append({"name": name, "args": args})
        except Exception as e:
            log.warning("Не удалось распарсить tool call: %s: %s", json_str, e)
    return tool_calls


async def process_request_with_llm(
    user_message: str, expression_score: Dict
) -> str:
    """Обрабатывает запрос за 1 проход LLM (или 2 только при обращении к БД)."""
    global _ollama_oom_blocked_until
    log.info("Вопрос: %s", user_message)

    now = time.time()
    if now < _ollama_oom_blocked_until:
        remaining = int(_ollama_oom_blocked_until - now)
        log.info("Ollama заблокирован после OOM, осталось %d сек", remaining)
        return "Сова думает... подожди немного."
    _ollama_oom_blocked_until = 0.0

    # Быстрая реакция на мат без запуска нейросети
    if get_mat_count(expression_score) > 0:
        raw_result = await trigger_violent_mode()
        res = raw_result[0] if isinstance(raw_result, tuple) else raw_result
    else:
        try:
            # ЕДИНЫЙ ПРОХОД: модель либо сразу отвечает голосом, либо вызывает инструмент
            ai_message = await llm_agent.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ])

            tool_calls = ai_message.tool_calls or _parse_llm_tool_calls(
                ai_message.content or ""
            )

            if tool_calls:
                # Берем только первый релевантный инструмент, чтобы не делать лишних циклов
                tool_call = tool_calls[0]
                tool_name = tool_call["name"]
                log.info("Сова вызывает инструмент: %s", tool_name)

                tool_func = TOOLS_MAP.get(tool_name)
                if tool_func:

                    tool_args = tool_call.get("args", {})
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}

                    raw_result = await tool_func.ainvoke(tool_args)

                    if isinstance(raw_result, tuple) and len(raw_result) == 2:
                        tool_output, is_direct_answer = raw_result
                    else:
                        tool_output, is_direct_answer = raw_result, True

                    if is_direct_answer:
                        res = str(tool_output)
                    else:
                        # Второй проход делаем ТОЛЬКО если надо озвучить сырые факты из Qdrant/поиска
                        flat_prompt = (
                            f"Вопрос: '{user_message}'. Факты: {tool_output}. "
                            f"Ответь язвительно и по делу на основе фактов."
                        )
                        final_response = await llm_base.ainvoke([
                            {"role": "system", "content": VOICE_SYSTEM_PROMPT},
                            {"role": "user", "content": flat_prompt},
                        ])
                        res = final_response.content or ""
                else:
                    res = "Инструмент не найден"
            else:
                # Инструменты не потребовались — сразу забираем ответ первого прохода!
                res = ai_message.content or ""

        except Exception as e:
            error_msg = str(e).lower()
            if "out of memory" in error_msg or "cuda" in error_msg:
                _ollama_oom_blocked_until = time.time() + 30
                log.error("CUDA OOM -- блокируем Ollama на 30 сек: %s", e)
                return "Сова перегрелась, подумай покороче."
            log.error("Ошибка инференса Совы: %s", e)
            return "Не удалось обработать запрос"

    # --- Быстрая постобработка текста для TTS ---
    res = re.sub(r"<think>.*?</think>", "", res or "", flags=re.DOTALL)
    res = RE_CHINESE.sub("", res or "")
    for symbol in ("\u221a", "\u2248", "/", "\u03c0", "\u00b2", "\u00b3"):
        res = res.replace(symbol, "")

    res = RE_CLEAN_TEXT.sub(" ", res)
    res = RE_SPACES.sub(" ", res).strip()

    log.info("--> Ответ: %s", res)
    return res
