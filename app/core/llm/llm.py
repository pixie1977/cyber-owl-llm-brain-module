"""
Модуль LLM-агента с разделением на 3 изолированных режима:
1. 'crazy' (по умолчанию) — чистая генерация без tools (максимальная скорость, 0 пустых ответов).
2. 'consultant' — строгий поиск по Qdrant + озвучка фактов.
3. 'tools' — быстрый вызов бытовых инструментов.
"""

import json
import re
import time
from typing import Dict

from langchain_ollama import ChatOllama
from num2words import num2words

from app.config.config import MBB_OLLAMA_MODEL_NAME
from app.core.llm.promts import PROMPT_DEFAULT_CRAZY, PROMPT_CONSULTANT, PROMPT_CONSULTANT_VOICE, PROMPT_TOOLS
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

# --- 1. НАСТРОЙКА ИНСТАНСОВ (Единый num_ctx=2048 для защиты от переаллокации VRAM) ---

llm_crazy = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    temperature=0.45,
    repeat_penalty=1.18,
    num_ctx=2048,
    num_predict=180,
    keep_alive="15m",
    reasoning=False,
)

llm_consultant = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    temperature=0.15,
    repeat_penalty=1.15,
    num_ctx=2048,
    num_predict=1024,
    keep_alive="15m",
    reasoning=False,
).bind_tools([search_knowledge_base])

action_tools = [
    time_tool,
    math_tool,
    roll_dice_tool,
    joke_tool,
    toast_tool,
    trigger_vicious_response,
    not_understand_this,
]
TOOLS_MAP = {getattr(t, "name", getattr(t, "__name__", "")): t for t in action_tools}

llm_tools = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    base_url="http://localhost:11434",
    temperature=0.05,
    repeat_penalty=1.1,
    num_ctx=2048,
    num_predict=200,
    keep_alive="15m",
    reasoning=False,
).bind_tools(action_tools)

# --- 2. РЕГУЛЯРКИ И СЛОЙ МАРШРУТИЗАЦИИ (позже легко заменить на триграммы) ---

RE_THINK = re.compile(r"<think>.*?(?:</think>|$)", re.DOTALL)
RE_TOOL_JSON = re.compile(
    r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}',
    re.DOTALL,
)
RE_CHINESE = re.compile(r"[\u4e00-\u9fff]+")
RE_CLEAN_TEXT = re.compile(r"[^а-яА-ЯёЁa-zA-Z0-9\s.,!?]")
RE_SPACES = re.compile(r"\s+")

RE_MODE_CONSULTANT = re.compile(
    r"\b(консультант|справка|база|найди|поищи|что такое|кто такой|расскажи про|объясни|поясни за)\b",
    re.IGNORECASE,
)
RE_MODE_TOOLS = re.compile(
    r"\b(время|который час|посчитай|сколько будет|синус|косинус|тангенс|корень|степен|кубик|кости|спасбросок|шутк|анекдот|тост|поздрав|макс)\b",
    re.IGNORECASE,
)


def _number_to_words(text: str) -> str:
    """Заменяет все целые числа в тексте на словесное представление."""
    def _replace_number(match: re.Match) -> str:
        num = int(match.group())
        try:
            return num2words(num, lang='ru')
        except Exception:
            return match.group()

    return re.sub(r'\d+', _replace_number, text)

_ollama_oom_blocked_until = 0.0


def classify_intent(text: str) -> str:
    """
    Точка входа для классификации намерения.
    Сейчас работает на регулярках, позже сюда подключается триграммный индекс.
    """
    clean = text.strip()
    if RE_MODE_CONSULTANT.search(clean):
        log.warning("Профиль - консультант")
        return "consultant"
    if RE_MODE_TOOLS.search(clean):
        log.warning("Профиль - инструмент")
        return "tools"
    log.warning("Профиль - шиза")
    return "crazy"


def _extract_tool_call(ai_message) -> dict | None:
    """Извлекает первый tool_call из нативного ответа или текста."""
    if ai_message.tool_calls:
        return ai_message.tool_calls[0]

    content = ai_message.content or ""
    if "{" not in content:
        return None

    for json_str in RE_TOOL_JSON.findall(content):
        try:
            data = json.loads(json_str)
            name = data.get("name", "")
            args = data.get("arguments", {})
            if name and isinstance(args, dict):
                return {"name": name, "args": args}
        except Exception as e:
            log.warning("Ошибка парсинга JSON tool call: %s: %s", json_str, e)
    return None


def _parse_args(raw_args) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}
    return {}


async def process_request_with_llm(
    user_message: str, expression_score: Dict
) -> str:
    global _ollama_oom_blocked_until
    log.info("Вопрос: %s", user_message)

    now = time.time()
    if now < _ollama_oom_blocked_until:
        remaining = int(_ollama_oom_blocked_until - now)
        log.info("Ollama заблокирован после OOM, осталось %d сек", remaining)
        return "Сова думает... подожди немного."
    _ollama_oom_blocked_until = 0.0

    # Мгновенная реакция на мат без запуска LLM
    if get_mat_count(expression_score) > 0:
        raw_result = await trigger_violent_mode.ainvoke({})
        res = raw_result[0] if isinstance(raw_result, tuple) else raw_result
    else:
        mode = classify_intent(user_message)
        log.info("Выбран режим: %s", mode)

        try:
            if mode == "tools":
                ai_msg = await llm_tools.ainvoke([
                    {"role": "system", "content": PROMPT_TOOLS},
                    {"role": "user", "content": user_message},
                ])
                tool_call = _extract_tool_call(ai_msg)

                if tool_call and tool_call["name"] in TOOLS_MAP:
                    tool_name = tool_call["name"]
                    log.info("Вызов инструмента: %s", tool_name)
                    raw_result = await TOOLS_MAP[tool_name].ainvoke(
                        _parse_args(tool_call.get("args"))
                    )
                    if isinstance(raw_result, tuple) and len(raw_result) == 2:
                        res = str(raw_result[0])
                    else:
                        res = str(raw_result)
                else:
                    # Если триггер сработал ложно — отвечаем в базовом режиме
                    fallback = await llm_crazy.ainvoke([
                        {"role": "system", "content": PROMPT_DEFAULT_CRAZY},
                        {"role": "user", "content": user_message},
                    ])
                    res = fallback.content or ""

            elif mode == "consultant":
                ai_msg = await llm_consultant.ainvoke([
                    {"role": "system", "content": PROMPT_CONSULTANT},
                    {"role": "user", "content": user_message},
                ])
                tool_call = _extract_tool_call(ai_msg)

                if tool_call and tool_call["name"] == "search_knowledge_base":
                    log.info("Консультант лезет в Qdrant")
                    raw_result = await search_knowledge_base.ainvoke(
                        _parse_args(tool_call.get("args"))
                    )
                    facts = (
                        raw_result[0]
                        if isinstance(raw_result, tuple)
                        else raw_result
                    )
                    final_resp = await llm_crazy.ainvoke([
                        {"role": "system", "content": PROMPT_CONSULTANT_VOICE},
                        {
                            "role": "user",
                            "content": f"Вопрос: {user_message}. Факты из базы: {facts}",
                        },
                    ])
                    res = final_resp.content or ""
                else:
                    res = ai_msg.content or ""

            else:
                # Режим по умолчанию ('crazy') — один сверхбыстрый проход без tools
                ai_msg = await llm_crazy.ainvoke([
                    {"role": "system", "content": PROMPT_DEFAULT_CRAZY},
                    {"role": "user", "content": user_message},
                ])
                res = ai_msg.content or ""

        except Exception as e:
            error_msg = str(e).lower()
            if "out of memory" in error_msg or "cuda" in error_msg:
                _ollama_oom_blocked_until = time.time() + 30
                log.error("CUDA OOM -- блокируем Ollama на 30 сек: %s", e)
                return "Сова перегрелась, подумай покороче."
            log.error("Ошибка инференса Совы: %s", e)
            return "Не удалось обработать запрос"

    # --- Постобработка для TTS ---
    res = RE_THINK.sub("", res or "")
    res = RE_CHINESE.sub("", res)
    for symbol in ("\u221a", "\u2248", "/", "\u03c0", "\u00b2", "\u00b3"):
        res = res.replace(symbol, "")

    # Все числа → слова для TTS
    res = _number_to_words(res)

    res = RE_CLEAN_TEXT.sub(" ", res)
    res = RE_SPACES.sub(" ", res).strip()

    log.info("--> Ответ: %s", res)
    return res
