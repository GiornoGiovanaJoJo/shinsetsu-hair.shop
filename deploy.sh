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

# 5. Устанавливаем и перезапускаем systemd-сервис
echo "→ Настраиваем systemd-сервис..."
cp shinsetsu-hair.service /etc/systemd/system/shinsetsu-hair.service
systemctl daemon-reload
systemctl enable shinsetsu-hair

echo "→ Перезапускаем приложение..."
systemctl restart shinsetsu-hair
sleep 3

# 6. Проверяем, что приложение запустилось
if systemctl is-active --quiet shinsetsu-hair; then
    echo "✓ Приложение запущено через systemd"
else
    echo "✗ ОШИБКА: Приложение не запустилось!"
    echo "Последние строки лога:"
    journalctl -u shinsetsu-hair --no-pager -n 10
    exit 1
fi

echo "=== Деплой завершён успешно! ==="
