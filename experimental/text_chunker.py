import json
import re
import requests


class LaptopHeavyChunker:

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b",
    ):
        self.url = f"{ollama_url}/api/chat"
        self.model = model_name

    def clean_and_parse_json(self, text: str) -> dict:
        """Продвинутый парсер для исправления мелких синтаксических ошибок ИИ."""
        # 1. Вырезаем только то, что находится внутри первой и последней фигурных скобок
        match = re.search(r"(\{.*?\})", text, re.DOTALL)
        if match:
            text = match.group(1)

        text = text.strip()

        # 2. Пытаемся распарсить напрямую
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 3. Эвакуационный ремонт: исправление частых ошибок (неэкранированные переносы строк внутри кавычек)
        # Ищем значения полей и заменяем внутренние переносы строк на пробелы
        text = re.sub(
            r'("summary"\s*:\s*")(.*?)("\s*,\s*"content")',
            lambda m: m.group(1)
            + m.group(2).replace("\n", " ").replace("\r", "")
            + m.group(3),
            text,
            flags=re.DOTALL,
        )
        text = re.sub(
            r'("title"\s*:\s*")(.*?)("\s*,\s*"category")',
            lambda m: m.group(1)
            + m.group(2).replace("\n", " ").replace("\r", "")
            + m.group(3),
            text,
            flags=re.DOTALL,
        )

        # 4. Пробуем распарсить исправленный вариант
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Если все совсем плохо, собираем структуру вручную через регулярные выражения
            print("  [Коррекция]: Прямой разбор не удался, собираю регулярками...")
            title_match = re.search(r'"title"\s*:\s*"(.*?)"', text)
            cat_match = re.search(r'"category"\s*:\s*"(.*?)"', text)
            sum_match = re.search(r'"summary"\s*:\s*"(.*?)"', text, re.DOTALL)

            return {
                "title": title_match.group(1) if title_match else "Без названия",
                "category": cat_match.group(1) if cat_match else "Разное",
                "summary": (
                    sum_match.group(1).replace("\n", " ")
                    if sum_match
                    else "Не удалось извлечь резюме"
                ),
                "content": "",
            }

    def segment_archive(self, input_file: str, output_file: str):
        print(f"[Вертикаль]: Загружаю массив данных из {input_file}...")
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                full_text = f.read()
        except FileNotFoundError:
            print(f"❌ [Ошибка]: Файл {input_file} не найден.")
            return

        system_instructions = (
            "Ты — аналитик. Сделай краткий разбор текста. "
            "Ответь СТРОГО в формате JSON:\n"
            '{"title": "название", "category": "Безопасность/Вертикаль/Биохимия/Работа", '
            '"summary": "краткая суть", "content": ""}\n'
            "Внутри значений строк запрещено использовать неэкранированные кавычки и переносы строк."
        )

        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        current_chunk_buffer = ""
        processed_chunks = []

        print(
            f"[Контур Инференса]: Запуск отказоустойчивой сборки на модели {self.model}..."
        )

        total_paragraphs = len(paragraphs)
        for i, p in enumerate(paragraphs):
            current_chunk_buffer += p + "\n\n"

            if len(current_chunk_buffer) > 2000 or i == total_paragraphs - 1:
                chunk_id = len(processed_chunks) + 1
                print(
                    f"\n🚀 Нарезаю блок {chunk_id}... (Параграф {i+1}/{total_paragraphs})"
                )

                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_instructions},
                        {
                            "role": "user",
                            "content": f"Разбери этот текст:\n\n{current_chunk_buffer}",
                        },
                    ],
                    "stream": True,
                    "options": {
                        "temperature": 0.1,
                        "num_ctx": 4096,
                    },
                }

                try:
                    response = requests.post(
                        self.url, json=payload, timeout=None, stream=True
                    )
                    response.raise_for_status()

                    raw_response = ""
                    print("  [Live-Генерация]: ", end="", flush=True)

                    for line in response.iter_lines():
                        if line:
                            chunk = json.loads(line.decode("utf-8"))
                            token = (
                                chunk.get("message", {})
                                .get("content", "")
                            )
                            raw_response += token
                            print(token, end="", flush=True)

                    print()

                    if not raw_response.strip():
                        raise ValueError("Ollama вернула пустой поток")

                    # Очищаем маркдаун
                    if raw_response.strip().startswith("```"):
                        raw_response = (
                            raw_response.replace("```json", "")
                            .replace("```", "")
                            .strip()
                        )

                    # Безопасный парсинг с автоисправлением структуры
                    parsed_json = self.clean_and_parse_json(raw_response)

                    # Принудительно сохраняем исходный текст в кусок матрицы
                    parsed_json["content"] = current_chunk_buffer.strip()

                    processed_chunks.append(parsed_json)
                    print(
                        f"  ✅ [Успешно записано]: \"{parsed_json.get('title')}\" [{parsed_json.get('category')}]"
                    )

                except Exception as e:
                    print(f"  [Пропуск блока]: Необратимая ошибка: {e}")
                    processed_chunks.append({
                        "title": f"Аварийный блок {chunk_id}",
                        "category": "Не размечено",
                        "summary": f"Сбой парсинга: {str(e)}",
                        "content": current_chunk_buffer.strip(),
                    })

                current_chunk_buffer = ""

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_chunks, f, ensure_ascii=False, indent=2)

        print(
            f"\n🎉 [Протокол завершен]: Фрактальная матрица сохранена в {output_file}"
        )


if __name__ == "__main__":
    chunker = LaptopHeavyChunker(model_name="qwen2.5:7b")
    chunker.segment_archive("samanta_log.txt", "structured_qdrant_ready.json")
