import json
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer


def upload_matrix_to_qdrant(json_file: str, collection_name: str = "samanta_archive", url="http://localhost:6333"):
    # 1. Подключаемся к уже запущенному локальному Qdrant (по умолчанию порт 6333)
    print("[Контур Сети]: Подключение к локальному Qdrant...")
    client = QdrantClient(url=url)

    # 2. Инициализируем локальную модель эмбеддингов
    # Модель paraphrase-multilingual дает отличный векторный баланс для русского и английского языков
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"[Контур Эмбеддингов]: Загрузка модели {model_name}...")
    encoder = SentenceTransformer(model_name)

    # Получаем размерность вектора модели (для MiniLM-L12 это 384)
    vector_size = encoder.get_sentence_embedding_dimension()

    # 3. Загружаем нарезанную матрицу из файла
    print(f"[Матрица Данных]: Чтение {json_file}...")
    with open(json_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # 4. Пересоздаем или создаем коллекцию в Qdrant
    print(f"[Векторный Контур]: Проверка коллекции '{collection_name}'...")

    # Проверяем, существует ли коллекция, чтобы случайно не стереть старую, либо создаем заново
    collections = client.get_collections().collections
    exists = any(c.name == collection_name for c in collections)

    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE  # Косинусное сходство идеально для текстового поиска
            )
        )
        print(f"  [Успешно]: Создана новая коллекция {collection_name} с размерностью {vector_size}")
    else:
        print(f"  [Контур Активен]: Коллекция {collection_name} уже существует. Добавляю данные...")

    # 5. Генерация векторов и массовая загрузка (Upsert)
    print(f"[Инференс Векторов]: Начинаю загрузку {len(chunks)} точек...")

    points = []
    for idx, chunk in enumerate(chunks):
        # Строим вектор по summary и title для лучшего семантического поиска,
        # так как исходный лог может быть слишком шумным
        text_to_vector = f"Название: {chunk.get('title')}\nСуть: {chunk.get('summary')}"
        vector = encoder.encode(text_to_vector).tolist()

        # Формируем полезную нагрузку (Payload)
        payload = {
            "title": chunk.get("title", "Без названия"),
            "category": chunk.get("category", "Не размечено"),
            "summary": chunk.get("summary", ""),
            "content": chunk.get("content", "")  # Исходный текст куска для RAG
        }

        # Создаем точку для Qdrant
        points.append(
            models.PointStruct(
                id=idx,
                vector=vector,
                payload=payload
            )
        )

    # Загружаем пачкой в Qdrant
    client.upsert(
        collection_name=collection_name,
        points=points
    )

    print(f"✅ [Протокол Завершен]: Все {len(points)} смысловых блоков успешно интегрированы в Qdrant.")


if __name__ == "__main__":
    upload_matrix_to_qdrant("structured_qdrant_ready.json")
