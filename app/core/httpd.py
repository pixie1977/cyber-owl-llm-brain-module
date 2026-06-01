#!/usr/bin/env python3
"""
HTTP-сервер на FastAPI для STT с поддержкой GET и POST.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config.config import MBB_DOC_ROOT
from app.core.behaviour import Behaviour
from app.core.data import TextRequest, FaceDetection
from app.core.logger import get_logger

# --- Настройка логирования ---
log = get_logger(__name__)


behaviour:Behaviour = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 1. ЭТО вызовется ПРИ ЗАВЕРШЕНИИ СОЗДАНИЯ (СТАРТЕ) ----
    global behaviour
    behaviour = Behaviour()
    behaviour.start()
    print("Поведенческий модуль запущен!")
    yield
    # ---- 2. ЭТО вызовется ПРИ ЗАВЕРШЕНИИ РАБОТЫ (СТОПЕ) ----
    print("Поведенческий модуль останавливается...")

app = FastAPI(title="STT API Server", lifespan=lifespan)

# Подключаем статические файлы
print(f"MBB_DOC_ROOT={MBB_DOC_ROOT}")
app.mount("/static", StaticFiles(directory=MBB_DOC_ROOT), name="static")


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
    global behaviour
    question = request.text.strip()
    await behaviour.post_user_query(question)
    return {"status": "success", "received_text": latest_question}

@app.post("/image_detect")
async def receive_image_detect(request: list[FaceDetection]) -> dict:

    raw_data = [item.model_dump() for item in request]

    log.info(f"Received image detect: {raw_data}")

    await behaviour.post_faces(request)

    return {"status": "success"}

@app.get("/latest")
async def get_latest_transcript() -> dict:
    global latest_question
    """
    Возвращает последний полученный текст.

    Returns:
        JSON с полем `transcript` (или пустой строкой, если текста нет).
    """
    return {"transcript": latest_question or ""}