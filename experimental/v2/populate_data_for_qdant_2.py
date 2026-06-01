import os
import json
import ollama

OLLAMA_MODEL = "qwen2.5:3b"


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 300):
    """Нарезает длинный текст на чанки с перекрытием."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def enrich_chunk_with_qwen(chunk_text: str, session_id: str, chunk_index: int) -> dict:
    """Прогоняет чанк через Qwen для создания выжимки и вопросов."""
    print(f"🤖 [Qwen] Обрабатываю чанк №{chunk_index} для сессии {session_id}...")

    prompt = f"""
    Ты — технический аналитик полевых технологий. Проанализируй данный текстовый кусок технической инструкции.
    Выполни две задачи:
    1. Сделай краткую выжимку этого куска (1-2 sentences).
    2. Напиши 3 конкретных вопроса на русском языке, которые инженер может задать по этому тексту.

    Формат ответа строго JSON (без markdown-тегов ```json):
    {{
        "summary": "текст выжимки",
        "questions": ["вопрос 1", "вопрос 2", "вопрос 3"]
    }}

    Текст чанка:
    {chunk_text}
    """

    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
        raw_json = response['response'].strip().replace("```json", "").replace("```", "")
        data = json.loads(raw_json)
    except Exception as e:
        print(f"⚠️ Ошибка парсинга JSON от Qwen: {e}. Применяю дефолт.")
        data = {"summary": "Техническая инструкция полевого оборудования.", "questions": []}

    return data


def process_file_to_struct(file_path: str, session_id: str) -> list:
    """Парсит один файл и возвращает список структурированных объектов."""
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    chunks = chunk_text(raw_text)
    session_data = []
    print("всего chuncks = "+str(len(chunks)))

    for idx, chunk in enumerate(chunks):
        enriched = enrich_chunk_with_qwen(chunk, session_id, idx)

        # Формируем идеальный плоский текст для будущего эмбеддинга (HyDE)
        text_to_embed = (
            f"Сессия: {session_id}. "
            f"Суть: {enriched['summary']}. "
            f"Ключевые вопросы: {' '.join(enriched['questions'])}. "
            f"Оригинальный текст: {chunk}"
        )

        print(text_to_embed)

        session_data.append({
            "session_id": session_id,
            "chunk_index": idx,
            "text_to_embed": text_to_embed,
            "payload": {
                "session_id": session_id,
                "chunk_index": idx,
                "summary": enriched['summary'],
                "full_instruction": chunk,
                "generated_questions": enriched['questions']
            }
        })
    return session_data


if __name__ == "__main__":
    # Список ваших исходных файлов сессий
    files_to_process = [
        {"path": "forest_tech.txt", "id": "FOREST_TECHNOLOGY"},
        # {"path": "session_2.txt", "id": "SESSION_DRILLING"}
    ]

    all_prepared_data = []
    for f_info in files_to_process:
        structured_chunks = process_file_to_struct(f_info["path"], f_info["id"])
        all_prepared_data.extend(structured_chunks)

    # Сохраняем в промежуточный JSON
    output_filename = "ready_to_upload.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_prepared_data, f, ensure_ascii=False, indent=4)

    print(f"\n🎉 Этап 1 завершен! Создан структурированный файл: {output_filename}")
    print(f"Всего подготовлено квантов для базы: {len(all_prepared_data)}")
