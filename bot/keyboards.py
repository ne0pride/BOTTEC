from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup,ReplyKeyboardMarkup, KeyboardButton
from database import Database

# Клавиатура для подписки
async def subscribe_keyboard(channel_link: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=channel_link)],
        [InlineKeyboardButton(text="✅ Подписался", callback_data="sub_check")]
    ])
    return keyboard

# Главное меню
async def main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Каталог"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="ℹ️ FAQ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


CATEGORIES_PER_PAGE = 3  # Количество категорий на странице. Можно сделать, что бы пользователь задавал сам,
# сколько он хочет видеть на странице
async def categories_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру с категориями (с пагинацией)."""
    db = Database()
    categories = await db.get_categories()
    total_pages = (len(categories) - 1) // CATEGORIES_PER_PAGE + 1
    start, end = page * CATEGORIES_PER_PAGE, (page + 1) * CATEGORIES_PER_PAGE
    buttons = [[InlineKeyboardButton(text=cat["name"], callback_data=f"category_{cat['id']}")] for cat in categories[start:end]]

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="Вперёд ➡", callback_data=f"page_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=buttons + [navigation_buttons] if navigation_buttons else buttons)

SUBCATEGORIES_PER_PAGE = 3  # Количество подкатегорий на одной странице

async def subcategories_keyboard(category_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру с подкатегориями (с пагинацией)."""
    db = Database()
    subcategories = await db.get_subcategories(category_id)
    total_pages = (len(subcategories) - 1) // SUBCATEGORIES_PER_PAGE + 1
    start, end = page * SUBCATEGORIES_PER_PAGE, (page + 1) * SUBCATEGORIES_PER_PAGE
    buttons = [[InlineKeyboardButton(text=sub["name"], callback_data=f"subcategory_{sub['id']}")] for sub in subcategories[start:end]]

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"subcat_page_{category_id}_{page - 1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="Вперёд ➡", callback_data=f"subcat_page_{category_id}_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=buttons + [navigation_buttons] if navigation_buttons else buttons)


async def product_navigation_keyboard(subcategory_id: int, product_index: int, total_products: int,
                                      product_id: int) -> InlineKeyboardMarkup:
    """Создаёт инлайн-клавиатуру для переключения товаров в подкатегории."""
    buttons = [
        [InlineKeyboardButton(text="🛒 Добавить в корзину", callback_data=f"add_to_cart_{product_id}")]
    ]

    navigation_buttons = []
    if product_index > 0:
        navigation_buttons.append(
            InlineKeyboardButton(text="⬅ Назад", callback_data=f"product_page_{subcategory_id}_{product_index - 1}"))
    if product_index < total_products - 1:
        navigation_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡", callback_data=f"product_page_{subcategory_id}_{product_index + 1}"))

    if navigation_buttons:
        buttons.append(navigation_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def confirm_keyboard():
    """Создает инлайн клавиатуру для подвеждрения добавления товара в корзине"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_cart"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_cart")]
    ])
    return keyboard



async def cart_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для корзины."""
    db = Database()
    cart_items = await db.get_cart(user_id)

    buttons = []
    if not cart_items:
        return None

    for item in cart_items:
        buttons.append([InlineKeyboardButton(text=f"❌ Удалить {item['name']}", callback_data=f"remove_{item['product_id']}")])

    buttons.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    buttons.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

