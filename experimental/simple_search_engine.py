import json

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
# Пробуем сделать сырой поиск прямо через векторный стор, минуя цепочки RAG
from llama_index.core.vector_stores import VectorStoreQuery

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "samanta_archive"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Инициализация компонентов
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Подключение
client = QdrantClient(QDRANT_URL)

# Хранилище с фиксацией текстового ключа
vector_store = QdrantVectorStore(
    client=client, collection_name=COLLECTION_NAME, text_key="content"
)

# Обертка в индекс LlamaIndex
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_vector_store(
    vector_store, storage_context=storage_context, embed_model=embeddings
)

# Создание поискового движка
retriever = index.as_retriever(similarity_top_k=3)



if __name__ == "__main__":

    # Пример тестового запроса (измените на свой, когда запустите)
    # engine.query("биохимический кризис или защита контура")

    while True:
        user_query = input(
            "Введите поисковый запрос (или 'exit' для выхода): "
        )
        if user_query.lower() == "exit":
            break
        if user_query.strip():
            # Запрашиваем информацию у поисковика
            nodes = retriever.retrieve(user_query)

            # Смотрим, что он нашел
            print(f"Найдено релевантных блоков: {len(nodes)}\n")

            for i, node in enumerate(nodes, 1):
                print(f"=== Результат №{i} (Сходство: {node.score:.4f}) ===")
                print(f"Текст чанка:\n{node.text}")

                # Можно вытащить метаданные, которые создали ранее
                meta = node.node.metadata
                print(f"Категория: {meta.get('category')}")
                print(f"Краткая суть: {meta.get('summary')}\n")

