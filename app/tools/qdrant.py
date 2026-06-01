"""
Модуль для поиска информации в базе знаний Qdrant.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.tools import tool
from qdrant_client import QdrantClient

from app.core.logger import get_logger

# Конфигурация
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "jet_knowledge_base"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"


log = get_logger(__name__)

# Инициализация компонентов
try:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    client = QdrantClient(QDRANT_URL)
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
except Exception as e:
    log.error(f"Ошибка инициализации компонента 'Qdrant vector store': {e}")
    vector_store = None


@tool
def search_knowledge_base(query: str, **kwargs) -> tuple[str, bool]:
    """

    Используется для получения информации о науке, мифах и других темах.

    Вызывай при наличии вопроса по научной области или интересующей темы.

    Примеры слов "расскажи", "что думаешь", "а как это работает?"

    Args:
        query: Поисковый запрос от пользователя.

    Returns:
        Строка с объединённым содержанием наиболее релевантных документов.
        Если документы не найдены — сообщение об отсутствии информации.
    """
    if not vector_store:
        return "Векторная база недоступна по техническим причинам.", False

    docs = vector_store.similarity_search(query, k=3)

    if not docs:
        return "В базе знаний информации не найдено.", False

    return "\n---\n".join(doc.page_content for doc in docs), False