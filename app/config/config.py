"""
Конфигурационный файл приложения STT.
Загружает переменные окружения и устанавливает значения по умолчанию.
"""

import os
from distutils.util import strtobool
from dotenv import load_dotenv


# Определяем текущую директорию
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Загружаем .env файл
load_dotenv()


# Проверка обязательной переменной
MBB_USE_TORCH_MODEL_MANAGER_STR = os.getenv("MBB_USE_TORCH_MODEL_MANAGER_STR")
if not MBB_USE_TORCH_MODEL_MANAGER_STR:
    raise ValueError("Не задан MBB_USE_TORCH_MODEL_MANAGER_STR в .env")

MBB_USE_TORCH_MODEL_MANAGER_STR = strtobool(MBB_USE_TORCH_MODEL_MANAGER_STR)

# Настройки сервера
MBB_PORT = os.getenv("MBB_PORT")
if not MBB_PORT:
    raise ValueError("Не задан MBB_PORT в .env")
MBB_PORT = int(MBB_PORT)

MBB_HOST = os.getenv("MBB_HOST")
if not MBB_HOST:
    raise ValueError("Не задан MBB_HOST в .env")

MBB_LOG_LEVEL = os.getenv("MBB_LOG_LEVEL")
if not MBB_LOG_LEVEL:
    raise ValueError("Не задан MBB_LOG_LEVEL в .env")

MBB_URL_TO_TEXT_TRANSMIT = os.getenv("MBB_URL_TO_TEXT_TRANSMIT")

MBB_LOGS_DIR = os.getenv("MBB_LOGS_DIR")

MBB_DOC_ROOT = os.getenv("MBB_DOC_ROOT")

MBB_OLLAMA_MODEL_NAME = os.getenv("MBB_OLLAMA_MODEL_NAME")

MBB_PRINT_THINKING_LOG = os.environ.get('MBB_PRINT_THINKING_LOG')
if not MBB_PRINT_THINKING_LOG:
    MBB_PRINT_THINKING_LOG = False
else:
    MBB_PRINT_THINKING_LOG = bool(strtobool(MBB_PRINT_THINKING_LOG))

TTS_URL = os.getenv("TTS_URL")
if not TTS_URL:
    raise ValueError("Не задан TTS_URL в .env")