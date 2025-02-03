import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логов (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - [%(levelname)s] - %(message)s",  # Формат логов
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),  # Лог в файл
        logging.StreamHandler()  # Вывод в консоль
    ],
)

# Создаём объект логирования
logger = logging.getLogger(__name__)
