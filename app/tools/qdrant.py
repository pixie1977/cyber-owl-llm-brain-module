"""
Модуль для поиска информации в базе знаний Qdrant.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.tools import tool
from qdrant_client import QdrantClient

# Конфигурация
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "jet_knowledge_base"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

# Инициализация компонентов
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
client = QdrantClient(QDRANT_URL)
vector_store = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)


@tool
def search_knowledge_base(query: str, **kwargs) -> tuple[str, bool]:
    """
    Выполняет поиск в базе знаний по заданному запросу.

    Используется для получения информации о гипотезе Эверетта, науке, мифах и других темах.

    Args:
        query: Поисковый запрос от пользователя.

    Returns:
        Строка с объединённым содержанием наиболее релевантных документов.
        Если документы не найдены — сообщение об отсутствии информации.
    """
    docs = vector_store.similarity_search(query, k=3)

    if not docs:
        return "В базе знаний информации не найдено.", False

    return "\n---\n".join(doc.page_content for doc in docs), False