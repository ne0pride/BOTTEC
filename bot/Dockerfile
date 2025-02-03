# Используем Python 3.10
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВСЁ содержимое bot (включая скрытые файлы)
COPY . .


# Запускаем бота
CMD ["python", "bot.py"]
