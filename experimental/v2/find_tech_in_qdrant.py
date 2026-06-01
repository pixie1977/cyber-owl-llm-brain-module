import httpx
import ollama
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# КОНФИГУРАЦИЯ БАЗЫ И МОДЕЛИ
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "forest_technologies"
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_MODEL = "qwen2.5:3b"

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Хранилище с фиксацией текстового ключа
vector_store = QdrantVectorStore(
    client=client, collection_name=COLLECTION_NAME
)

# Обертка в индекс LlamaIndex
storage_context = StorageContext.from_defaults(vector_store=vector_store)

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

# 1. Явно инициализируем модель эмбеддингов и LLM через LlamaIndex классы
embed_model = OllamaEmbedding(model_name="nomic-embed-text")

# 1. Создаем кастомный HTTP-клиент с увеличенным временем ожидания (300 секунд / 5 минут)
# Если железо совсем медленное, можно поставить None (бесконечное ожидание)
custom_http_client = httpx.Client(timeout=300.0)

# 2. Передаем этот клиент в инициализацию Ollama
llm = Ollama(
    model="qwen2.5:3b",
    request_timeout=300.0,      # Тайм-аут для внутренних сценариев LlamaIndex
    additional_kwargs={"timeout": 300.0} # Проброс тайм-аута в API-запросы
)

# 2. Подключаем клиент Qdrant
client = QdrantClient(host="localhost", port=6333)
vector_store = QdrantVectorStore(collection_name=COLLECTION_NAME, client=client)

# 3. Настраиваем контекст хранения
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 4. Собираем индекс. Передаем объект embed_model, чтобы пройти проверку isinstance
index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    storage_context=storage_context,
    embed_model=embed_model
)

# 5. Создаем поисковый движок с нашей Qwen
query_engine = index.as_query_engine(llm=llm)

retriever = index.as_retriever(similarity_top_k=5)


def retrieve_and_assemble(query_topic: str) -> str:
    print(f"🔍 Ищу релевантные компоненты в Qdrant по запросу: '{query_topic}'...")

    nodes = retriever.retrieve(query_topic)

    # Отправляем запрос и получаем структурированный документ
    response = query_engine.query(query_topic)
    return str(response)


# --- ЗАПУСК СБОРКИ ---
if __name__ == "__main__":
    # Задаем тему, которую хотим вытащить и собрать в один документ
    topic = ("как сделать активированный уголь из дерева")

    final_document = retrieve_and_assemble(topic)

    print("\n================ ИТОГОВЫЙ СТРУКТУРИРОВАННЫЙ ДОКУМЕНТ ================\n")
    print(final_document)

