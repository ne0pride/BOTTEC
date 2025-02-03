import os

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, ContentType
from aiogram import F

from aiogram import Bot, types
import re
from config import CHANNEL, YOOKASSA_PROVIDER_TOKEN
from keyboards import subscribe_keyboard, main_keyboard, categories_keyboard, subcategories_keyboard, \
    product_navigation_keyboard, confirm_keyboard, cart_keyboard
from logger import logger
from database import Database
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
router = Router()

class OrderState(StatesGroup):
    waiting_for_address = State()
    waiting_for_phone = State()
    waiting_for_payment = State()

class CartState(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_confirmation = State()

class FAQState(StatesGroup):
    waiting_for_answer = State()


async def check_subscription(user_id: int, bot):
    """Проверяем подписан ли на канал"""
    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        is_subscribed = chat_member.status in ["member", "administrator", "creator"]

        logger.info(f"👤 Проверка подписки: User {user_id} {'ПОДПИСАН' if is_subscribed else 'НЕ подписан'}")
        return is_subscribed
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке подписки у User {user_id}: {e}")
        return False  # На случай ошибки считаем, что не подписан


@router.message(Command("start"))
async def start_handler(message: types.Message, bot):
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    full_name = message.from_user.full_name
    db = Database()
    await db.add_user(user_id, username, full_name)
    if not await check_subscription(user_id, bot):
        logger.warning(f"🚨 {user_id} не подписан и получил сообщение с просьбой подписаться.")
        await message.answer(
            "❌ Вы не подписаны на канал!\n"
            "Для использования бота, подпишитесь и нажмите '✅ Подписался'.",
            reply_markup=await subscribe_keyboard(f"https://t.me/{CHANNEL.lstrip('@')}")
        )
        return
    logger.info(f"✅ {user_id} подписан")
    await message.answer("Выберите действие:", reply_markup=await main_keyboard())

@router.callback_query(lambda c: c.data == "sub_check")
async def check_subscription_callback(callback: types.CallbackQuery, bot):
    user_id = callback.from_user.id
    if await check_subscription(user_id, bot):
        logger.info(f"✅ {user_id} подписалс")
        await callback.message.answer("Выберите действие:", reply_markup=await main_keyboard())
    else:
        logger.warning(f"🚨{user_id} нажал '✅ Подписался', но не подписавлся")
        await callback.answer("❌ Вы всё ещё не подписаны!", show_alert=True)

@router.message(lambda message: message.text == "📦 Каталог")
async def catalog_handler(message: types.Message):
    logger.info(f"📦 {message.from_user.id} открыл каталог.")
    await message.answer("📦 Выберите категорию:", reply_markup=await categories_keyboard(page=0))

@router.callback_query(lambda c: c.data.startswith("page_"))
async def pagination_callback(callback: types.CallbackQuery):
    """Обрабатывает кнопки пагинации."""
    page = int(callback.data.split("_")[1])
    logger.info(f"📄 {callback.from_user.id} переключил страницу на {page}.")
    keyboard = await categories_keyboard(page)
    await callback.message.edit_text("📦 Выберите категорию:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("category_"))
async def category_callback(callback: types.CallbackQuery):
    """Обрабатывает выбор категории и показывает подкатегории."""
    category_id = int(callback.data.split("_")[1])
    logger.info(f"✅ {callback.from_user.id} выбрал категорию ID {category_id}.")
    keyboard = await subcategories_keyboard(category_id, page=0)
    await callback.message.edit_text("🔍 Выберите подкатегорию:", reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("subcat_page_"))
async def subcategory_pagination_callback(callback: types.CallbackQuery):
    """Обрабатывает кнопки пагинации подкатегорий."""
    try:
        data_parts = callback.data.split("_")
        category_id = int(data_parts[2])  # ID категории
        page = int(data_parts[3])  # Номер страницы

        logger.info(f"📄 {callback.from_user.id} листает подкатегории категории {category_id}, страница {page}.")
        keyboard = await subcategories_keyboard(category_id, page)
        await callback.message.edit_text("🔍 Выберите подкатегорию:", reply_markup=keyboard)

    except ValueError as e:
        logger.error(f"❌ Ошибка обработки пагинации подкатегорий: {e}")
        await callback.answer("❌ Ошибка загрузки подкатегорий.")


@router.callback_query(lambda c: c.data.startswith("subcategory_"))
async def subcategory_callback(callback: types.CallbackQuery):
    """Обрабатывает выбор подкатегории и показывает первый товар."""
    subcategory_id = int(callback.data.split("_")[1])
    db = Database()
    products = await db.get_products_by_subcategory(subcategory_id)

    if products:
        product = products[0]  # Берём первый товар
        total_products = len(products)
        logger.info(f"🛍 User {callback.from_user.id} смотрит товар {product['name']} (ID {product['id']}).")

        text = f"🛍 *{product['name']}*\n💰 Цена: ${product['price']}\n📜 {product['description']}"
        keyboard = await product_navigation_keyboard(subcategory_id, 0, total_products, product['id'])

        await callback.message.delete()
        await callback.message.answer_photo(photo=product['image_url'], caption=text, reply_markup=keyboard,
                                            parse_mode="Markdown")
    else:
        await callback.answer("❌ В этой подкатегории пока нет товаров.")


@router.callback_query(lambda c: c.data.startswith("product_page_"))
async def product_pagination_callback(callback: types.CallbackQuery):
    """Обрабатывает кнопки пагинации товаров (по одному)."""
    try:
        data_parts = callback.data.split("_")
        subcategory_id = int(data_parts[2])  # ID подкатегории
        product_index = int(data_parts[3])  # Индекс товара

        db = Database()
        products = await db.get_products_by_subcategory(subcategory_id)

        if 0 <= product_index < len(products):
            product = products[product_index]
            logger.info(
                f"🛍 {callback.from_user.id} листает товар {product['name']} (ID {product['id']}), позиция {product_index}.")

            text = f"🛍 *{product['name']}*\n💰 Цена: ${product['price']}\n📜 {product['description']}"
            keyboard = await product_navigation_keyboard(subcategory_id, product_index, len(products), product['id'])

            await callback.message.delete()
            await callback.message.answer_photo(photo=product['image_url'], caption=text, reply_markup=keyboard,
                                                parse_mode="Markdown")
        else:
            await callback.answer("❌ Ошибка загрузки товара.")

    except (ValueError, IndexError) as e:
        logger.error(f"❌ Ошибка обработки пагинации товаров: {e}")
        await callback.answer("❌ Ошибка загрузки товаров.")


@router.callback_query(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart_callback(callback: types.CallbackQuery, state: FSMContext):
    """Запрашивает количество товара для добавления в корзину."""
    try:
        data = callback.data.split("_")
        product_id = int(data[3])
        await state.update_data(product_id=product_id)
        await state.set_state(CartState.waiting_for_quantity)
        logger.info(f"🛒 {callback.from_user.id} выбрал товар {product_id}, запрашиваем количество.")
        await callback.message.delete()
        await callback.message.answer("🔢 Введите количество товаров (число):")

    except ValueError as e:
        logger.error(f"❌ Ошибка обработки добавления в корзину: {e}")
        await callback.answer("❌ Ошибка при добавлении в корзину.")


@router.message(CartState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    """Проверяет, что введено корректное число, и запрашивает подтверждение."""
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число.")
        return

    quantity = int(message.text)
    if quantity < 1:
        await message.answer("❌ Количество должно быть не менее 1.")
        return

    await state.update_data(quantity=quantity)
    await state.set_state(CartState.waiting_for_confirmation)

    logger.info(f"🛒 {message.from_user.id} выбрал {quantity} шт., ждем подтверждения.")
    await message.answer(f"Добавить {quantity} шт. в корзину?", reply_markup=await confirm_keyboard())

@router.callback_query(lambda c: c.data == "confirm_cart")
async def confirm_cart_callback(callback: types.CallbackQuery, state: FSMContext):
    """Добавляет товар в корзину после подтверждения."""
    data = await state.get_data()
    user_id = callback.from_user.id
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    db = Database()
    await db.add_to_cart(user_id, product_id, quantity)

    logger.info(f"✅ {user_id} добавил {quantity} шт. товара {product_id} в корзину.")
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("✅ Товар добавлен в корзину!\n\n📍 Главное меню:", reply_markup=await main_keyboard())

@router.callback_query(lambda c: c.data == "cancel_cart")
async def cancel_cart_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена добавления в корзину."""
    await state.clear()
    logger.info(f"❌ {callback.from_user.id} отменил добавление в корзину.")
    await callback.message.delete()
    await callback.message.edit_text("❌ Добавление в корзину отменено.")





@router.message(lambda message: message.text == "🛒 Корзина")
async def show_cart_handler(message: types.Message):
    """Показывает содержимое корзины пользователя."""
    db = Database()
    cart_items = await db.get_cart(message.from_user.id)

    if not cart_items:
        await message.answer("🛒 Ваша корзина пуста.")
        return

    text = "🛒 *Ваша корзина:*\n"
    total_price = 0

    for item in cart_items:
        item_total = float(item['price']) * item['quantity']
        total_price += item_total
        text += f"🔹 {item['name']} - {item['quantity']} шт. *${item_total:.2f}*\n"

    text += f"\n💰 *Итого: ${total_price:.2f}*"

    keyboard = await cart_keyboard(message.from_user.id)

    logger.info(f"🛒 User {message.from_user.id} открыл корзину.")
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(lambda c: c.data.startswith("remove_"))
async def remove_from_cart_callback(callback: types.CallbackQuery):
    """Удаляет товар из корзины."""
    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    db = Database()

    await db.remove_from_cart(user_id, product_id)
    logger.info(f"🗑 {user_id} удалил товар ID {product_id} из корзины.")

    await callback.answer("✅ Товар удалён.")
    await callback.message.delete()

    # Обновляем корзину
    keyboard = await cart_keyboard(user_id)
    if keyboard:
        await callback.message.answer("🛒 *Обновлённая корзина:*", reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.message.answer("🛒 Ваша корзина пуста.")

@router.callback_query(lambda c: c.data == "clear_cart")
async def clear_cart_callback(callback: types.CallbackQuery):
    """Очищает всю корзину пользователя."""
    user_id = callback.from_user.id
    db = Database()

    await db.clear_cart(user_id)
    logger.info(f"🗑 {user_id} очистил корзину.")

    await callback.answer("🗑 Корзина очищена.")
    await callback.message.delete()
    await callback.message.answer("🛒 Ваша корзина пуста.")

@router.callback_query(lambda c: c.data == "checkout")
async def checkout_callback(callback: types.CallbackQuery, state: FSMContext):
    """Запрашивает адрес доставки."""
    await state.set_state(OrderState.waiting_for_address)
    logger.info(f"📦{callback.from_user.id} начал оформление заказа.")
    await callback.message.delete()
    await callback.message.answer("📍 Введите ваш адрес доставки:")


@router.message(OrderState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    """Сохраняет адрес и запрашивает номер телефона."""
    await state.update_data(address=message.text)
    await state.set_state(OrderState.waiting_for_phone)

    logger.info(f"📍 {message.from_user.id} ввёл адрес: {message.text}")

    await message.answer("📞 Введите ваш номер телефона:")



@router.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext, bot: Bot):
    try:
        """Сохраняет телефон, создаёт заказ и отправляет Invoice в Telegram."""
        phone_pattern = re.compile(r"^\+?\d{10,15}$")  # Проверяем, что номер состоит из 10-15 цифр

        if not phone_pattern.match(message.text):
            await message.answer("❌ Ошибка: Введите корректный номер телефона (10-15 цифр, можно с `+`).")
            return

        await state.update_data(phone=message.text)
        data = await state.get_data()
        user_id = message.from_user.id
        address = data.get("address")
        phone = data.get("phone")

        db = Database()
        cart_items = await db.get_cart(user_id)

        if not cart_items:
            await message.answer("❌ Ошибка: ваша корзина пуста.")
            await state.clear()
            return

        # Переводим сумму в копейки
        total_price_cents = sum(int(round(float(item['price']) * item['quantity'] * 100)) for item in cart_items)

        # Проверяем минимальную сумму заказа (100 рублей = 10000 копеек)
        MIN_ORDER_AMOUNT_CENTS = 10000  # 100 рублей
        if total_price_cents < MIN_ORDER_AMOUNT_CENTS:
            await message.answer(f"❌ Ошибка: минимальная сумма заказа - 100 рублей.\nВаш заказ: {total_price_cents / 100:.2f} RUB.")
            await state.clear()
            return

        order_id = await db.create_order(user_id, address, phone, total_price_cents / 100)  # Храним сумму в рублях

        for item in cart_items:
            await db.add_order_item(order_id, item["product_id"], item["quantity"])

        await state.set_state(OrderState.waiting_for_payment)

        logger.info(f"💰 User {user_id} оформил заказ #{order_id} на сумму {total_price_cents / 100:.2f} RUB.")

        prices = [
            types.LabeledPrice(
                label=f"{item['name']} ({item['quantity']} шт.)",
                amount=int(round(float(item['price']) * item['quantity'] * 100))  # Переводим в копейки
            )
            for item in cart_items
        ]

        await bot.send_invoice(
            chat_id=user_id,
            title="Оплата заказа",
            description=f"Заказ #{order_id}, сумма: {total_price_cents / 100:.2f} RUB",
            provider_token=YOOKASSA_PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="order_payment",
            payload=str(order_id)
        )
        print('WQE')
    except Exception as e:
        logger.error(f" Error occurred while processing order: {e}")
        await message.answer("Ошибка: Произошла непредвиденная ошибка.")
        await state.clear()


@router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery, bot: Bot):
    """Подтверждает предварительный запрос на оплату."""
    try:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        print('W32QE')

    except Exception as e:
        print('Z asd')
        logger.error(f"Error occurred while processing pre-checkout query: {e}")


@router.message(lambda message: message.successful_payment)
async def process_successful_payment(message: types.Message, bot: Bot):
    """Обрабатывает успешную оплату."""
    try:
        print("✅ Оплата подтверждена")

        user_id = message.from_user.id
        order_id = int(message.successful_payment.invoice_payload)

        logger.info(f"✅  {user_id} оплатил заказ #{order_id}.")
        db = Database()
        await db.execute("UPDATE orders SET status = 'paid' WHERE order_id = $1", order_id)
        await bot.send_message(user_id, "✅ Оплата прошла успешно! Ваш заказ будет обработан.")

    except Exception as e:
        print("❌ Ошибка обработки платежа")
        logger.error(f"Error occurred while processing successful payment: {e}")
        await message.answer("Ошибка: Произошла непредвиденная ошибка.")

@router.message(Command("orders"))
async def send_orders_csv(message: types.Message, bot: Bot):
    """Отправляет CSV-файл со всеми заказами."""
    db = Database()
    file_path = await db.generate_orders_csv()

    if not file_path:
        await message.answer("📂 В базе данных нет заказов.")
        return

    # Отправляем CSV-файл
    await bot.send_document(message.chat.id, types.FSInputFile(file_path), caption="📦 Все заказы в CSV-файле")

    # Удаляем файл после отправки
    os.remove(file_path)

    logger.info(f"📂 User {message.from_user.id} запросил CSV с заказами.")


@router.message(lambda message: message.text == "ℹ️ FAQ")
async def show_faq_handler(message: types.Message):
    """Показывает список вопросов FAQ."""
    db = Database()
    faq_items = await db.get_faq()

    if not faq_items:
        await message.answer("ℹ️ FAQ пока пуст.")
        return

    text = "📌 *Часто задаваемые вопросы:*\n\n"
    buttons = []

    for item in faq_items:
        text += f"❓ {item['question']}\n"
        buttons.append([InlineKeyboardButton(text=item["question"], callback_data=f"faq_{item['id']}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    logger.info(f"ℹ️ {message.from_user.id} открыл FAQ.")
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(lambda c: c.data.startswith("faq_"))
async def faq_answer_callback(callback: types.CallbackQuery):
    """Показывает ответ на выбранный вопрос."""
    faq_id = int(callback.data.split("_")[1])
    db = Database()
    faq_items = await db.get_faq()

    for item in faq_items:
        if item["id"] == faq_id:
            logger.info(f"📌 {callback.from_user.id} прочитал ответ на FAQ: {item['question']}")
            await callback.message.edit_text(f"📌 *{item['question']}*\n\n{item['answer']}", parse_mode="Markdown")
            return

    await callback.answer("❌ Вопрос не найден.")

@router.message(FAQState.waiting_for_answer)
async def save_faq_answer(message: types.Message, state: FSMContext):
    """Сохраняет ответ в FAQ."""
    data = await state.get_data()
    question = data.get("question")
    answer = message.text

    db = Database()
    await db.add_faq(question, answer)

    logger.info(f"✅ Вопрос-ответ добавлен: {question} - {answer}")

    # Очищаем состояние FSM
    await state.clear()

    await message.answer("✅ Вопрос-ответ сохранён!")

@router.message()
async def auto_add_faq(message: types.Message, state: FSMContext):
    """Автоматически добавляет вопрос в FAQ, если его нет."""
    db = Database()
    existing_answer = await db.get_faq_by_question(message.text)

    if existing_answer:
        await message.answer(f"ℹ️ {existing_answer['answer']}")
        return

    await message.answer("❌ Вопрос не найден в базе. Введите ответ на него:")

    # Включаем состояние FSM
    await state.set_state(FAQState.waiting_for_answer)
    await state.update_data(question=message.text)

    logger.info(f"❓ Новый вопрос добавлен в ожидание ответа: {message.text}")





