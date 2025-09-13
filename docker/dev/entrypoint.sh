#!/bin/sh

# Ждем готовности базы данных
echo "Waiting for database to be ready..."
sleep 5

# Выполняем миграции
echo "Running migrations..."
python manage.py migrate

# Запускаем Django сервер
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8080