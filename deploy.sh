#!/bin/bash

# ==========================================
# Скрипт для ручного или автоматического деплоя
# ==========================================

# Переходим в директорию проекта
# Замените на реальный путь, где лежит проект на сервере
PROJECT_DIR="/var/www/shinsetsu-hair.shop"
cd $PROJECT_DIR || exit

echo "Начинаем деплой..."

# 1. Получаем последние обновления из git
echo "Стягиваем изменения из GitHub..."
git pull origin main # или master

# 2. Обновляем зависимости для Python
echo "Обновляем зависимости Python..."
# Если вы используете виртуальное окружение (рекомендуется):
# source venv/bin/activate
pip install -r requirements.txt

# 3. Перезапускаем сервис
# В зависимости от того, как вы запускаете приложение (uvicorn/fastapi)
# Рекомендуемый способ в Linux - использовать systemd. 
echo "Перезапускаем приложение..."
# Расскомментируйте нужную строку:

# Если через systemd:
# sudo systemctl restart shinsetsu.service

# Если через pm2 (для server.js или python):
# pm2 restart shinsetsu-api

# Если просто убиваете процесс и запускаете заново (не рекомендуется для прода):
# pkill -f "uvicorn main:app"
# nohup uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "Деплой успешно завершен!"
