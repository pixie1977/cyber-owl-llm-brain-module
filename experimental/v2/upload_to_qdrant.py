import json
import uuid
import ollama
from qdrant_client import QdrantClient
from qdrant_client.http import models

# КОНФИГУРАЦИЯ БАЗЫ
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "forest_technologies"
EMBEDDING_MODEL = "nomic-embed-text"  # Модель векторизации в Ollama

client = QdrantClient(host=QDRANT_HOST, point=QDRANT_PORT) if hasattr(QdrantClient, 'point') else QdrantClient(
    host=QDRANT_HOST, port=QDRANT_PORT)


def recreate_collection():
    """Пересоздает чистую коллекцию в Qdrant."""
    print(f"📦 Инициализация коллекции в Qdrant: {COLLECTION_NAME}")

    # Если старая коллекция есть — удаляем её, чтобы не плодить дубликаты
    try:
        client.delete_collection(collection_name=COLLECTION_NAME)
    except Exception:
        pass

    # Создаем заново (для nomic-embed-text размерность векторов строго 768)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=768,
            distance=models.Distance.COSINE
        )
    )


def upload_json_to_qdrant(json_file_path: str):
    """Читает готовый JSON, генерирует эмбеддинги и пушит в базу."""
    with open(json_file_path, "r", encoding="utf-8") as f:
        data_points = json.load(f)

    recreate_collection()

    print(f"🚀 Начинаю заливку {len(data_points)} точек в Qdrant...")

    points_to_upsert = []
    for item in data_points:
        # 1. Генерируем вектор из подготовленного на Этапе 1 текста
        emb_res = ollama.embeddings(model=EMBEDDING_MODEL, prompt=item["text_to_embed"])
        vector = emb_res['embedding']

        # 2. Упаковываем в структуру Qdrant
        points_to_upsert.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=item["payload"]
            )
        )

    # 3. Пушим всё одной транзакцией (батчем) для максимальной скорости
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points_to_upsert
    )
    print(f"🎉 База данных успешно обновлена! Все точки загружены в '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    input_json = "ready_to_upload.json"
    upload_json_to_qdrant(input_json)
