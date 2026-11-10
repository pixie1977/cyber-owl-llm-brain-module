#!/bin/bash
# 🐍 Скрипт запуска Cyber Owl LLM Brain
# Автоматически создаёт виртуальное окружение и устанавливает зависимости

set -e  # Прерывать выполнение при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

echo "🔍 Определяем окружение..."

# Проверяем, существует ли виртуальное окружение
if [ ! -d "$VENV_DIR" ]; then
    echo "📁 Виртуальное окружение не найдено. Создаём venv..."
    python -m venv "$VENV_DIR"

    echo "📦 Устанавливаем зависимости из requirements.txt..."
    if [ ! -f "$REQUIREMENTS" ]; then
        echo "❌ Файл requirements.txt не найден!"
        exit 1
    fi

    # Активируем и устанавливаем
    source "$VENV_DIR/bin/activate"
    pip install -r "$REQUIREMENTS"

    echo "✅ Виртуальное окружение создано и зависимости установлены."
else
    echo "✅ Используем существующее виртуальное окружение."
    source "$VENV_DIR/bin/activate"
fi

# Проверяем наличие .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "   Создайте .env на основе README.md или используйте значения по умолчанию."
    echo "   Запуск продолжится с возможными ошибками конфигурации."
fi

# Запуск приложения
echo "🚀 Запуск Cyber Owl LLM Brain..."
echo "   Для остановки нажмите Ctrl+C"

echo "=== Фоновый прогрев ИИ-буфера ==="

# Даем ИИ-серверу Ollama, который перезапустился силами systemd, 4 секунды на стабилизацию
sleep 4

echo "Отправляем прогревочный запрос для фиксации 9B модели в CUDA..."
curl -X POST http://localhost:11434/api/generate -d '{"model": "sova-mod","prompt": "hi", "stream": false}' > /dev/null

echo "=== Память заблокирована под Ollama. Запускаем проект Cyber Owl... ==="
sleep 1

export OLLAMA_NUM_PARALLEL=1

exec python -m app.main
