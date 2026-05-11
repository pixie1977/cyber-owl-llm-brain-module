# tests/test_qdrant_indexation.py
import os
import time

import pytest
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Путь к тестовому файлу
TEST_FILE = Path("tests/data/plank.txt")

# Конфигурация (должна совпадать со скриптом)
QDRANT_URL = "http://localhost:6333"
TEST_COLLECTION_NAME = "jet_knowledge_base"  # Отдельная коллекция для тестов
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
VECTOR_SIZE = 384
IS_AFTER_CLEAR = False


@pytest.fixture(scope="session")
def qdrant_client():
    """Создаёт клиент Qdrant."""
    client = QdrantClient(QDRANT_URL)
    yield client


@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_collection(qdrant_client):
    """Создаёт тестовую коллекцию перед тестом и удаляет после."""
    if not qdrant_client.collection_exists(TEST_COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=TEST_COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    yield

    if IS_AFTER_CLEAR:
        # Очистка после теста
        if qdrant_client.collection_exists(TEST_COLLECTION_NAME):
            qdrant_client.delete_collection(TEST_COLLECTION_NAME)


def test_load_single_txt_into_qdrant(qdrant_client):
    """Тестирует загрузку plank.txt в Qdrant."""
    from app.qdrant_indexation_script import load_single_txt

    # Убедимся, что файл существует
    assert TEST_FILE.exists(), f"Тестовый файл {TEST_FILE} не найден."

    # Выполняем загрузку
    docs = load_single_txt(file_path=TEST_FILE, collection_name=TEST_COLLECTION_NAME)

    # Проверяем, что документы загружены
    assert len(docs) > 0, "Документы не были разбиты на фрагменты."

    # Ожидание индексации (до 10 секунд)
    for _ in range(10):
        collection_info = qdrant_client.get_collection(TEST_COLLECTION_NAME)
        if collection_info.points_count > 0:
            break
        time.sleep(1)

    # Проверяем количество точек в коллекции
    collection_info = qdrant_client.get_collection(TEST_COLLECTION_NAME)
    assert collection_info.points_count > 0, "Векторы не были добавлены в Qdrant."
    assert collection_info.points_count == len(
        docs
    ), "Количество векторов в Qdrant не совпадает с количеством документов."

    print(f"✅ Успешно загружено {collection_info.points_count} векторов в Qdrant.")