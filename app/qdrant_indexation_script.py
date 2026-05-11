"""
Скрипт для индексации PDF и TXT-документов в Qdrant с помощью Hugging Face embeddings.
Поддерживает передачу пути к файлу или папке через аргумент командной строки.
"""

import os
import sys
from pathlib import Path
from typing import List

import click
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams


# --- КОНФИГУРАЦИЯ ---
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "jet_knowledge_base"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
VECTOR_SIZE = 384  # Размер эмбеддингов для модели multilingual-e5-small


def load_single_txt(file_path: Path, collection_name: str = COLLECTION_NAME) -> List:
    """
    Загружает и разбивает один TXT-файл на фрагменты и загружает в Qdrant.

    Args:
        file_path (Path): Путь к текстовому файлу.

    Returns:
        List: Список обработанных документов.
        :param file_path:
        :param collection_name:
    """
    print(f"→ Обработка текстового файла: {file_path}")
    try:
        loader = TextLoader(str(file_path), encoding="utf-8")
        documents = loader.load()
    except Exception as e:
        print(f"❌ Ошибка при загрузке TXT-файла {file_path}: {e}")
        return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    # Инициализация модели эмбеддингов (после определения всех функций)
    print(f"Загрузка модели эмбеддингов: {collection_name}")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    try:
        QdrantVectorStore.from_documents(
            docs,
            embeddings,
            url=QDRANT_URL,
            collection_name=collection_name,
        )
        print(f"✅ Успешно загружено {len(docs)} фрагментов из {file_path.name}")
    except Exception as e:
        print(f"❌ Ошибка при загрузке в Qdrant: {e}")
        return []

    return docs


def load_single_pdf(file_path: Path) -> List:
    """
    Загружает и разбивает один PDF-файл.

    Args:
        file_path (Path): Путь к PDF-файлу.

    Returns:
        List: Список документов.
    """
    print(f"→ Обработка PDF-файла: {file_path}")
    loader = PyPDFLoader(str(file_path))
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    try:
        return loader.load_and_split(text_splitter)
    except Exception as e:
        print(f"❌ Ошибка при загрузке PDF {file_path}: {e}")
        return []


def load_pdfs_from_directory(directory: Path) -> List:
    """
    Рекурсивно загружает все PDF-файлы из директории.

    Args:
        directory (Path): Путь к папке с PDF.

    Returns:
        List: Список всех документов.
    """
    all_docs = []
    pdf_files = list(directory.rglob("*.pdf"))
    if not pdf_files:
        print(f"⚠️ В папке {directory} не найдено PDF-файлов.")
        return all_docs

    print(f"Найдено {len(pdf_files)} PDF-файлов. Загрузка...")
    for pdf_file in pdf_files:
        docs = load_single_pdf(pdf_file)
        all_docs.extend(docs)

    return all_docs


def load_txts_from_directory(directory: Path) -> List:
    """
    Рекурсивно загружает все TXT-файлы из директории.

    Args:
        directory (Path): Путь к папке с TXT.

    Returns:
        List: Список всех документов.
    """
    all_docs = []
    txt_files = list(directory.rglob("*.txt"))
    if not txt_files:
        print(f"⚠️ В папке {directory} не найдено TXT-файлов.")
        return all_docs

    print(f"Найдено {len(txt_files)} TXT-файлов. Загрузка...")
    for txt_file in txt_files:
        docs = load_single_txt(txt_file)
        all_docs.extend(docs)

    return all_docs


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
)
def ingest_docs(path: Path, collection_name: str = COLLECTION_NAME):
    """
    Индексирует PDF и TXT-документы в векторную базу Qdrant.

    PATH: Путь к файлу (.pdf/.txt) или папке с документами.
    """
    # Инициализация клиента Qdrant
    print(f"Подключение к Qdrant: {QDRANT_URL}")
    client = QdrantClient(QDRANT_URL)

    # Создание коллекции, если не существует
    if not client.collection_exists(collection_name):
        print(f"Создаётся коллекция: {collection_name} (размер: {VECTOR_SIZE})")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    else:
        print(f"Коллекция {collection_name} уже существует. Данные будут добавлены.")

    # Загрузка документов
    documents = []

    if path.is_file():
        print(f"Обработка одного файла: {path}")
        if path.suffix.lower() == ".pdf":
            documents = load_single_pdf(path)
        elif path.suffix.lower() == ".txt":
            documents = load_single_txt(path)
        else:
            print(f"❌ Неподдерживаемый формат файла: {path.suffix}")
            sys.exit(1)
    else:
        print(f"Обработка папки: {path}")
        pdf_docs = load_pdfs_from_directory(path)
        txt_docs = load_txts_from_directory(path)
        documents = pdf_docs + txt_docs

    if not documents:
        print("❌ Нет документов для загрузки.")
        sys.exit(1)

    # Инициализация модели эмбеддингов (после определения всех функций)
    print(f"Загрузка модели эмбеддингов: {collection_name}")
    embeddings = HuggingFaceEmbeddings(model_name=collection_name)

    # Загрузка в Qdrant (если ещё не загружены в load_single_*)
    if any(doc.metadata.get("source", "").endswith(".pdf") for doc in documents):
        print(f"Загрузка {len(documents)} PDF-фрагментов в Qdrant...")
        try:
            QdrantVectorStore.from_documents(
                [doc for doc in documents if doc.metadata.get("source", "").endswith(".pdf")],
                embeddings,
                url=QDRANT_URL,
                collection_name=collection_name,
            )
        except Exception as e:
            print(f"❌ Ошибка при загрузке PDF в Qdrant: {e}")
            sys.exit(1)

    print(f"✅ Обработка завершена. Всего обработано: {len(documents)} документов.")


if __name__ == "__main__":
    ingest_docs()