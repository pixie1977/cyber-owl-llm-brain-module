#!/usr/bin/env python3
"""
HTTP-сервер на FastAPI для STT с поддержкой GET и POST.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from app.config.config import MBB_DOC_ROOT
from app.core.llm import process_request_with_llm
from app.integration.integration_adapter import send_mat_sign_servo, send_ready_servo, send_to_tts
from app.tools.brawl import get_mat_count
from app.tools.greetengs import get_greetengs
from app.utils.text.basic_text_utils import find_and_crop_by_keywords
from app.utils.text.expression_language_detector import expression_detector
from app.utils.text.levenstein_text_utils import similarity_ratio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 1. ЭТО вызовется ПРИ ЗАВЕРШЕНИИ СОЗДАНИЯ (СТАРТЕ) ----
    await send_ready_servo()
    await send_to_tts(get_greetengs())
    print("Поведенческий модуль запущен!")
    yield
    # ---- 2. ЭТО вызовется ПРИ ЗАВЕРШЕНИИ РАБОТЫ (СТОПЕ) ----
    print("Поведенческий модуль останавливается...")

app = FastAPI(title="STT API Server")

# Подключаем статические файлы
print(f"MBB_DOC_ROOT={MBB_DOC_ROOT}")
app.mount("/static", StaticFiles(directory=MBB_DOC_ROOT), name="static")


# Модель для входных данных
class TextRequest(BaseModel):
    text: str


# Глобальная переменная для хранения последнего вопроса
latest_question: Optional[str] = None
# Глобальная переменная для хранения последнего ответа
latest_response: Optional[str] = None


@app.post("/json")
async def receive_text(request: TextRequest) -> dict:
    """
    Принимает текст через POST-запрос и сохраняет его.

    Args:
        request: Объект с полем `text`.

    Returns:
        JSON с подтверждением.
    """
    global latest_question
    global latest_response
    question = request.text.strip()
    expression_score = expression_detector.analyze(question)
    mat_count = get_mat_count(expression_score)
    if mat_count>0:
        await send_mat_sign_servo(mat_count)
    question = find_and_crop_by_keywords(
        key_words=["совунья", "чувырло"],
        text=question,
        threshold=80
    )
    if question:
        latest_question = question
        # проверяем, что нам на вход не приехал наш же ответ
        similarity_score = similarity_ratio(latest_question, latest_response)
        if similarity_score < 0.5:
            latest_response = await process_request_with_llm(latest_question, expression_score)
    return {"status": "success", "received_text": latest_question}


@app.get("/latest")
async def get_latest_transcript() -> dict:
    global latest_question
    """
    Возвращает последний полученный текст.

    Returns:
        JSON с полем `transcript` (или пустой строкой, если текста нет).
    """
    return {"transcript": latest_question or ""}