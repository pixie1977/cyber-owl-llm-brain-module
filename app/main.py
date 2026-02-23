"""
Точка входа в приложение STT (Speech-to-Text).
Запускает сервер и фоновое прослушивание микрофона.
"""

import asyncio
from asyncio import set_event_loop

import uvicorn

from app.config.config import MBB_HOST, MBB_PORT, MBB_LOG_LEVEL
from app.core.httpd import app

if __name__ == "__main__":
    # Устанавливаем цикл событий
    # (иначе будут проблемы при запуске асинхронки в потоках)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    set_event_loop(loop)

    # Запускаем сервер
    config = uvicorn.Config(app=app, host=MBB_HOST, port=MBB_PORT, log_level=MBB_LOG_LEVEL, loop=loop)
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())