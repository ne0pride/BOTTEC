import asyncpg
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from logger import logger
import pandas as pd
class Database:
    """Класс для работы с БД"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """один экземпляр класса"""
        if not cls._instance:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация подключения."""
        if not hasattr(self, "pool"):
            self.pool = None

    async def connect(self):
        """Подключение к БД."""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    database=DB_NAME, user=DB_USER, password=DB_PASSWORD,
                    host=DB_HOST, port=DB_PORT
                )
                logger.info("✅ Подключено к базе данных.")
            except Exception as e:
                logger.error(f"❌ Ошибка подключения к БД: {e}")

    async def execute(self, query: str, *args):
        """Выполняет SQL-запрос (INSERT, UPDATE, DELETE)."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Выполняет SQL-запрос (SELECT) и возвращает список строк."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Выполняет SQL-запрос (SELECT) и возвращает одну строку."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def close(self):
        """Закрывает соединение с БД."""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Соединение с БД закрыто.")

    async def get_categories(self):
        """Получает список всех категорий."""
        return await self.fetch("SELECT id, name FROM categories")

    async def get_products_by_category(self, category_id: int):
        """Получает все товары по ID категории."""
        return await self.fetch("SELECT id, name, price FROM products WHERE category_id = $1", category_id)

    async def get_subcategories(self, category_id: int):
        """Получает список подкатегорий по ID категории."""
        return await self.fetch("SELECT id, name FROM subcategories WHERE category_id = $1", category_id)

    async def get_product_by_subcategory(self, subcategory_id: int):
        """Получает один товар из подкатегории."""
        return await self.fetchrow("SELECT * FROM products WHERE subcategory_id = $1 LIMIT 1", subcategory_id)

    async def get_products_by_subcategory(self, subcategory_id: int):
        """Получает список товаров по ID подкатегории."""
        return await self.fetch(
            "SELECT id, name, description, price, image_url FROM products WHERE subcategory_id = $1",
            subcategory_id)

    async def add_to_cart(self, user_id: int, product_id: int, quantity: int):
        """Добавляет товар в корзину или обновляет количество, если товар уже есть."""
        await self.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, product_id) DO UPDATE
            SET quantity = cart.quantity + EXCLUDED.quantity;
        """, user_id, product_id, quantity)

        logger.info(f"✅ {user_id} добавил {quantity} шт. товара {product_id} в корзину.")

    async def get_cart(self, user_id: int):
        """Получает содержимое корзины пользователя."""
        return await self.fetch("""
            SELECT c.product_id, p.name, p.price, c.quantity 
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = $1
        """, user_id)

    async def remove_from_cart(self, user_id: int, product_id: int):
        """Удаляет товар из корзины пользователя."""
        await self.execute("DELETE FROM cart WHERE user_id = $1 AND product_id = $2", user_id, product_id)
        logger.info(f"🗑 User {user_id} удалил товар ID {product_id} из корзины.")

    async def clear_cart(self, user_id: int):
        """Очищает корзину пользователя."""
        await self.execute("DELETE FROM cart WHERE user_id = $1", user_id)
        logger.info(f"🗑 User {user_id} очистил корзину.")

    async def create_order(self, user_id: int, address: str, phone: str, total_price: float) -> int:
        """Создаёт новый заказ и возвращает его ID."""
        order_id = await self.fetchrow("""
            INSERT INTO orders (user_id, address, phone, total_price)
            VALUES ($1, $2, $3, $4) RETURNING order_id;
        """, user_id, address, phone, total_price)
        return order_id["order_id"]

    async def add_order_item(self, order_id: int, product_id: int, quantity: int):
        """Добавляет товар в заказ."""
        await self.execute("""
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES ($1, $2, $3);
        """, order_id, product_id, quantity)

    async def get_order_items(self, order_id: int):
        """Получает список товаров в заказе."""
        return await self.fetch("""
            SELECT p.name, p.price, oi.quantity 
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = $1
        """, order_id)



    async def get_all_orders(self):
        """Получает список всех заказов из БД."""
        return await self.fetch("""
            SELECT o.order_id, o.user_id, o.address, o.phone, o.total_price, o.status, oi.product_id, p.name, oi.quantity
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            ORDER BY o.order_id DESC
        """)

    async def generate_orders_csv(self) -> str:
        """Создаёт CSV-файл со всеми заказами и возвращает путь к нему."""
        orders = await self.get_all_orders()

        if not orders:
            return None  # Если заказов нет

        # Конвертируем данные в DataFrame
        df = pd.DataFrame(orders)

        # Переименовываем столбцы для читаемости
        df.columns = ["Order ID", "User ID", "Address", "Phone", "Total Price (RUB)", "Status", "Product ID",
                      "Product Name", "Quantity"]

        # Создаём путь к файлу
        file_path = "orders.csv"

        # Сохраняем CSV
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        return file_path

    async def add_user(self, user_id: int, username: str, full_name: str):
        """Добавляет нового пользователя, если его нет в базе."""
        await self.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING;
        """, user_id, username, full_name)

        logger.info(f"👤 Новый пользователь: {user_id} - {full_name} (@{username})")

    async def add_faq(self, question: str, answer: str):
        """Добавляет новый вопрос-ответ в FAQ, если его нет."""
        await self.execute("""
            INSERT INTO faq (question, answer)
            VALUES ($1, $2)
            ON CONFLICT (question) DO UPDATE SET answer = EXCLUDED.answer;
        """, question, answer)

        logger.info(f"📌 Добавлен FAQ: {question}")

    async def get_faq(self):
        """Получает список всех вопросов и ответов."""
        return await self.fetch("SELECT id, question, answer FROM faq")

    async def get_faq_by_question(self, question: str):
        """Ищет ответ на вопрос в БД."""
        return await self.fetchrow("SELECT answer FROM faq WHERE question = $1", question)