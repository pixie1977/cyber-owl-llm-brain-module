"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
"""
import asyncio
import re
from typing import Any, Dict, List

from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from app.config.config import MBB_OLLAMA_MODEL_NAME, MBB_PRINT_THINKING_LOG, TTS_URL
from app.core.client import PostClient
from app.core.logger import get_logger
from app.tools.math import calculator
from app.tools.time import get_time
from app.utils.basic_text_utils import filter_text_math, process_time_answers, wrap_answer_with_ssml
from app.utils.number_to_words_ru import float_to_text_russian

# --- Настройка логирования ---
log = get_logger(__name__)


# --- Определение инструментов ---
@tool
def get_current_time() -> str:
    """
    Возвращает текущее время в формате ЧЧ:ММ.
    """
    current_time = get_time()
    log.info(f"Инструмент вызван: get_current_time -> {current_time}")
    return current_time


@tool
def calculate_math_expression(expression: str) -> str:
    """
    Выполняет математические вычисления с поддержкой дробей, корней, тригонометрии и pi.
    Работает в градусах. 'pi', 'π' интерпретируются как 180.
    Косинус - cos(), синус - sin().
    Тангенс - tan().
    """
    log.info(f"Инструмент вызван: calculate_math_expression с выражением '{expression}'")
    try:
        result = calculator(expression)
        log.debug(f"Результат калькулятора: {result}")
        return result
    except Exception as e:
        log.error(f"Ошибка в calculate_math_expression: {e}")
        return "Ошибка при вычислении"


# Список инструментов
tools = [
    get_current_time,
    calculate_math_expression,
]

# --- Настройка модели Ollama ---
llm = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    temperature=0.2,
    base_url="http://localhost:11434",
)
log.info("Модель LLM инициализирована: %s", llm.model)

# --- Системный промпт ---
system_prompt = (
    "Вы — полезный ИИ-ассистент по имени СОВА. "
    "Отвечайте как персонаж женского пола. "
    "Отвечайте на вопросы точно, кратко."
    "Отвечайте ТОЛЬКО по-русски. "
    "Если вызывался математический инструмент - ответьте только числом. Математические цитаты вида √2/2, ≈, √3 - из ответа ИСКЛЮЧИТЬ"
    "Используйте предоставленные инструменты, если необходимо получить данные. "
    "НИЧЕГО НЕ ПРИДУМЫВАЙТЕ! Если не знаете — скажите 'Без малейшего понятия'. "
    "Отвечайте быстро."
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
agent_executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)

log.info("Агент и исполнитель инициализированы.")


# --- Вспомогательные функции ---
def extract_numeric_result(calculator_output: str) -> float | None:
    """
    Извлекает числовое значение из строки вида "Результат: ... ≈ 42.0".
    """
    try:
        # Ищем число после "≈"
        match = re.search(r"≈\s*([+-]?[\d.]+)", calculator_output)
        if match:
            return float(match.group(1))
        # Или пробуем распарсить всю строку как число
        return float(calculator_output.strip())
    except (ValueError, AttributeError):
        return None


def analyze_tools_called(response) -> Dict[str, bool]:
    """
    Анализирует, какие инструменты были вызваны.
    """
    called = {"math": False, "time": False}

    tool_calls = []

    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_calls.extend(response.tool_calls)

    # Вывод названий всех вызванных инструментов
    names = [tc['name'] for tc in tool_calls]

    for tool_name in names:
        if tool_name == "calculate_math_expression":
            called["math"] = True
        elif tool_name == "get_current_time":
            called["time"] = True

    return called


async def process_request_with_llm(user_message: str) -> str:
    """
    Обрабатывает запрос пользователя через агента, применяет постобработку.
    """
    log.info(f"Вопрос: {user_message}")

    # Вызов агента
    try:
        response = agent_executor.invoke({
            "messages": [("human", user_message)]
        })
    except Exception as e:
        log.error(f"Ошибка при выполнении агента: {e}")
        res = "Не удалось обработать запрос"
        return res

    messages = response.get("messages")
    ai_msg = messages[-1]
    res = ai_msg.content
    res = re.sub(r'[\u4e00-\u9fff]+', '', res) # чистим иероглифы

    log.info("--> Ответ: "+res)

    # Отправка в TTS
    if res:
        try:
            wrapped_res = wrap_answer_with_ssml(res)
            async with PostClient(TTS_URL) as client:
                post_result = await client.post(text=wrapped_res)
            log.info(f"Результат отправки в TTS: {post_result}")
        except Exception as e:
            log.error(f"Ошибка при отправке в TTS: {e}")

    return res


# --- Пример использования ---
async def main():
    questions = [
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
        "что такое магнетар"
    ]
    for q in questions:
        await process_request_with_llm(q)


if __name__ == "__main__":
    asyncio.run(main())