"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
"""
import asyncio
from datetime import datetime
import logging
import re

from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from app.config.config import MBB_OLLAMA_MODEL_NAME, MBB_PRINT_THINKING_LOG, TTS_URL
from app.core.client import PostClient
from app.core.logger import get_logger
from app.tools.math import calculator
from app.tools.time import get_time
from app.utils.number_to_words_ru import float_to_text_russian
from app.utils.basic_text_utils import filter_text_math, process_time_answers, wrap_answer_with_ssml

# --- Настройка логирования ---
log = get_logger(__name__)

was_math_tool_used = False
was_time_tool_used = False


# --- Определение инструментов ---
@tool
def get_current_time() -> str:
    """Возвращает текущее время.

    Возможные примеры запросов:
    - Сколько время
    - Сколько времени
    - Который час
    - Скока ща

    Returns:
        Текущее время в формате ЧЧ:ММ.
    """
    global was_time_tool_used
    was_time_tool_used = True
    current_time = get_time()
    log.info(f"Инструмент вызван: get_current_time -> {current_time}")
    return f"{current_time}"


@tool
def calculate_math_expression(expression: str) -> str:
    """Выполняет математические вычисления с поддержкой дробей, корней, тригонометрии и pi.

    Работает в градусах. 'pi', 'π' интерпретируются как 180.
    Поддерживает:
      - sin, cos, tan, ctg
      - sqrt(x), √x
      - Дроби: 1/3, (2+1)/(4-2)
      - Упрощение выражений

    Args:
        expression: Математическое выражение для вычисления.

    Returns:
        Результат в формате: "Результат: {символьный} ≈ {численный}".
    """
    global was_math_tool_used
    log.info(f"Инструмент вызван: calculate_math_expression с выражением '{expression}'")
    was_math_tool_used = True
    return calculator(expression)


# Список инструментов
tools = [
    get_current_time,
    calculate_math_expression,
]

# --- Настройка модели Ollama ---
llm = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    temperature=0.7,
    base_url="http://localhost:11434",  # стандартный URL Ollama
)
log.info("Модель LLM инициализирована: %s", llm.model)

# --- Системный промпт ---
system_prompt = (
    "Вы — полезный ИИ-ассистент по имени СОВА. "
    "Отвечай как персонаж женского пола"
    "Отвечай на вопросы точно, кратко, по-русски. "
    "Используйте предоставленные инструменты, если необходимо получить данные. "
    "НИЧЕГО НЕ ПРИДУМЫВАЙ! Если не знаешь — просто ответь 'Без малейшего понятия'. "
    "Отвечай на вопросы БЫСТРО."
)

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=system_prompt),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)
log.info("Системный промпт и шаблон загружены.")

# --- Создание агента ---
agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=MBB_PRINT_THINKING_LOG,
    handle_parsing_errors=True,
)
log.info("Агент и исполнитель инициализированы.")

async def process_request_with_llm(user_message: str):
    global was_math_tool_used
    global was_time_tool_used
    log.info(f"Вопрос: {user_message}")
    log.info(f"Обработка вопроса: {user_message}")
    response = agent_executor.invoke({"input": user_message})
    res = f"{response.get('output').strip()}"
    if was_math_tool_used:
        was_math_tool_used = False
        res = filter_text_math(res)
        res = float_to_text_russian(res)
    if was_time_tool_used:
        was_time_tool_used = False
        res = process_time_answers(res)
    log.info(f"-->Ответ: {res}\n")
    if res:
        try:
            res = str(wrap_answer_with_ssml(res))
            async with PostClient(TTS_URL) as client:
                post_result = await client.post(text=res)
            log.info(post_result)
        except Exception as e:
            log.error(f"{e}")
    return res

# --- Пример использования ---
async def main():
    questions = [
        "косинус пи пополам",
        "пять плюс три в квадрате",
        "Который сейчас час?",
        "Расскажи о Париже",
        "Чему равно 15 * 4 + 10?",
        "Посчитай (5 + 3) ** 2",
        "Посчитай три плюс два в скобках и возвести в квадрат",
        "синус нуля",
        "синус тридцати градусов",
        "синус сорока пяти градусов",
        "что такое магнетар"
    ]
    for q in questions:
        await process_request(q)


if __name__ == "__main__":
    asyncio.run(main())
