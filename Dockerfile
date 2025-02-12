# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install watchdog

# Указываем переменные окружения
ENV PYTHONUNBUFFERED=1

# Команда для запуска Watchdog
CMD ["watchmedo", "auto-restart", "--recursive", "--pattern=*.py", "--", "python", "main.py"]
