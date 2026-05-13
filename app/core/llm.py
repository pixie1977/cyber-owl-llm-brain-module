"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
"""

import asyncio
import re
from typing import Dict

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama

from app.config.config import MBB_OLLAMA_MODEL_NAME
from app.core.logger import get_logger
from app.core.promts import system_prompt
from app.integration.integration_adapter import send_to_tts
from app.tools.brawl import get_mat_count, trigger_vicious_response
from app.tools.jokes import get_random_joke
from app.tools.math import calculate_math_expression
from app.tools.qdrant import search_knowledge_base
from app.tools.time import get_current_time_as_str


# --- Настройка логирования ---
log = get_logger(__name__)


# Список инструментов
tools = [
    get_current_time_as_str,
    calculate_math_expression,
    search_knowledge_base,
    get_random_joke,
    trigger_vicious_response,
]


# --- Настройка модели Ollama ---
llm = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    temperature=0.02,
    base_url="http://localhost:11434",
    num_ctx=128
)
log.info("Модель LLM инициализирована: %s", llm.model)
log.info("Системный промпт и шаблон загружены.")

structured_system_prompt = SystemMessage(content=system_prompt)

# --- Создание агента ---
agent_executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt=structured_system_prompt,
)
log.info("Агент и исполнитель инициализированы.")


async def process_request_with_llm(user_message: str, expression_score: Dict) -> str:
    """
    Обрабатывает запрос пользователя через агента, применяет постобработку.

    Args:
        user_message (str): Входной запрос.

    Returns:
        str: Готовый ответ для озвучивания.
        :param score:
    """
    log.info("Вопрос: %s", user_message)

    mat_count = get_mat_count(expression_score)
    if mat_count > 0:
        user_message = "ОБНАРУЖЕНО ХАМСТВО. ИСПОЛЬЗУЙ BATTLE_MODE: ELITE"

    try:
        response = await agent_executor.ainvoke(dict(messages=[("human", user_message)]))
    except Exception as e:
        log.error("Ошибка при выполнении агента: %s", e)
        res = "Не удалось обработать запрос"
        return res

    messages = response.get("messages")
    ai_msg = messages[-1]
    res = ai_msg.content
    res = re.sub(r'[\u4e00-\u9fff]+', '', res)  # убираем иероглифы

    # Чистим математические символы
    math_symbols = ['√', '≈', '/', 'π', '²', '³']
    for symbol in math_symbols:
        res = res.replace(symbol, '')

    log.info("--> Ответ: %s", res)

    # Отправка в TTS
    if res.strip():
        await send_to_tts(res)
    return res


# --- Пример использования ---
async def main():
    """Запуск тестовых запросов."""
    questions = [
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