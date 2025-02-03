# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Указываем переменную окружения для Django
ENV PYTHONUNBUFFERED 1

# Запускаем сервер Django
CMD ["python", "myproject/manage.py", "runserver", "0.0.0.0:8000"]
