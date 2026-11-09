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

# Добавь это в start.sh перед запуском Python логгера:
echo "Очищаем кэш и принудительно закрепляем модель в памяти..."
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
sleep 1

curl -X POST http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:9b",
  "prompt": "hi",
  "stream": false
}' > /dev/null

echo "Модель заблокирована в CUDA. Запускаем ноды робота..."
sleep 2


export OLLAMA_NUM_PARALLEL=1

exec python -m app.main
