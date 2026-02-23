#!/usr/bin/env python3
"""
HTTP-сервер на FastAPI для STT с поддержкой GET и POST.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from app.config.config import MBB_DOC_ROOT
from app.core.llm import process_request_with_llm
from app.utils.levenstein_text_utils import similarity_ratio

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
    latest_question = request.text.strip()

    #проверяем, что нам на вход не приехалл наш же ответ
    similarity_score = similarity_ratio(latest_question, latest_response)
    if similarity_score < 0.5:
        latest_response = await process_request_with_llm(latest_question)
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