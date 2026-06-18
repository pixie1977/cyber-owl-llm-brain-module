"""
Модуль инициализации LLM-агента с инструментами и системным промптом.
"""

import asyncio
import re
from typing import Dict

from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama

from app.config.config import MBB_OLLAMA_MODEL_NAME
from app.core.logger import get_logger
from app.core.llm.promts import system_prompt
from app.tools.brawl import get_mat_count, trigger_vicious_response, trigger_violent_mode, not_understand_this
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
]

# --- Настройка модели Ollama ---
# инструменты подключаем напрямую
# ландграф убивает кэш и производительность джетсона
# Инициализируем модель с фиксом зацикливания
llm = ChatOllama(
    model=MBB_OLLAMA_MODEL_NAME,
    temperature=0.2,
    base_url="http://localhost:11434",
    num_ctx=2048,
    model_kwargs={
        "repeat_penalty": 1.2, # Защита от повторения фраз
    }
).bind_tools(tools)

log.info("Модель LLM инициализирована: %s", llm.model)
log.info("Системный промпт и шаблон загружены.")

structured_system_prompt = SystemMessage(content=system_prompt)


async def process_request_with_llm(user_message: str, expression_score: Dict) -> str:
    """Обрабатывает запрос пользователя напрямую через нативный Tool Calling Ollama."""
    log.info("Вопрос: %s", user_message)

    mat_count = get_mat_count(expression_score)
    if mat_count > 0:
        res = trigger_violent_mode()
    else:
        try:
            # 1. Делаем первый быстрый запрос к Ollama (благодаря 'sova' промпт уже в кэше GPU!)
            ai_message = await llm.ainvoke(  # Убедитесь, что ваш массив сообщений для API выглядит именно так:
                [
                    {"role": "system", "content": system_prompt},  # Ваш промпт для СОВЫ
                    {"role": "user", "content": user_message}
                ]
            )

            # 2. Проверяем, хочет ли модель вызвать инструмент
            if ai_message.tool_calls:
                for tool_call in ai_message.tool_calls:
                    log.info("Сова вызывает инструмент: %s", tool_call["name"])

                    # Ищем нужную функцию в нашем списке инструментов
                    tool_func = next(
                        (t for t in tools if getattr(t, "name", getattr(t, "__name__", None)) == tool_call["name"]), None)
                    if tool_func:
                        # Выполняем инструмент локально
                        tool_output, is_direct_answer = tool_func.invoke(tool_call["args"])

                        if is_direct_answer is True:
                            res = tool_output
                        else:
                            # Отправляем результат обратно модели для финального ответа
                            final_response = await llm.ainvoke([
                                {"role": "system", "content": system_prompt},  # Ваш промпт для СОВЫ
                                {"role": "user", "content": user_message},
                                ai_message,
                                {"role": "tool", "content": str(tool_output), "tool_call_id": tool_call["id"]}
                            ])
                            res = final_response.content
                    else:
                        res = "Инструмент не найден"
            else:
                # Если инструменты не нужны, берем прямой ответ модели
                res = ai_message.content

        except Exception as e:
            log.error("Ошибка инференса Совы: %s", e)
            return "Не удалось обработать запрос"

    # --- Твоя постобработка текста для TTS ---
    res = re.sub(r'[\u4e00-\u9fff]+', '', res)  # убираем иероглифы
    math_symbols = ['√', '≈', '/', 'π', '²', '³']
    for symbol in math_symbols:
        res = res.replace(symbol, '')

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
