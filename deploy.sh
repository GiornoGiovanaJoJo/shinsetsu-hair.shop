#!/bin/bash

# ==========================================
# Деплой shinsetsu-hair.shop
# ==========================================

set -e

PROJECT_DIR="/root/shinsetsu-hair"

echo "=== Деплой shinsetsu-hair.shop ==="

# 1. Переход в директорию проекта
cd "$PROJECT_DIR" || { echo "ОШИБКА: Директория $PROJECT_DIR не найдена!"; exit 1; }
echo "✓ Директория: $PROJECT_DIR"

# 2. Разрешаем git операции
git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null

# 3. Получаем последние обновления из git
echo "→ Стягиваем изменения из GitHub..."
git pull origin main
echo "✓ Код обновлён"

# 4. Обновляем зависимости Python
echo "→ Обновляем зависимости..."
pip3 install --break-system-packages -r requirements.txt -q
echo "✓ Зависимости установлены"

# 5. Перезапускаем приложение
echo "→ Перезапускаем приложение..."
pkill -f "python3 main.py" 2>/dev/null || true
sleep 1

nohup python3 main.py > app.log 2>&1 &
NEW_PID=$!
sleep 3

# 6. Проверяем, что приложение запустилось
if kill -0 $NEW_PID 2>/dev/null; then
    echo "✓ Приложение запущено (PID: $NEW_PID)"
else
    echo "✗ ОШИБКА: Приложение не запустилось!"
    echo "Последние строки лога:"
    tail -10 app.log
    exit 1
fi

echo "=== Деплой завершён успешно! ==="
