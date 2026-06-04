import logging
import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8789819533:AAESS2xsCpwJkniX7jq3oRggcOBF3AhDYG4")

# HTTP сервер чтобы Render не засыпал
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bonnybaby bot is running!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# Умные ответы по ключевым словам
SMART_REPLIES = {
    ("коляска", "коляску", "коляски"): "🛝 *Коляска прогулочная*\n\nСтоимость проката: от *35 руб/нед*\nЛёгкие и манёвренные модели для города.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("автокресло", "кресло", "кресла"): "🚗 *Автокресло 0–13 кг*\n\nСтоимость проката: от *15 руб/нед*\nПроверены на безопасность, продезинфицированы.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("кроватка", "кроватку", "кровать"): "🛏️ *Кроватка с матрасом*\n\nСтоимость проката: от *20 руб/нед*\nВ комплекте матрас.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("качели", "качелей", "шезлонг"): "🪄 *Качели-шезлонг*\n\nСтоимость проката: от *45 руб/нед*\nЭлектронные и механические модели.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("манеж", "манежа"): "🎪 *Манеж игровой*\n\nСтоимость проката: от *20 руб/нед*\nСкладной, с дном.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("стульчик", "стул", "кормление"): "🥤 *Стульчик для кормления*\n\nСтоимость проката: от *20 руб/нед*\nРегулируемая высота и спинка.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("ходунки", "ходунков"): "🐘 *Ходунки*\n\nСтоимость проката: от *20 руб/нед*\nДля детей от 6 месяцев.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("прыгунки", "прыгунков"): "🏋️ *Прыгунки*\n\nСтоимость проката: от *20 руб/нед*\nКрепятся на дверной проём.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("пылесос", "пылесоса"): "🧹 *Моющий пылесос*\n\nСтоимость проката: от *50 руб/сут*\nГлубокая чистка ковров и мягкой мебели.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("пароочиститель",): "♨️ *Пароочиститель*\n\nСтоимость проката: от *35 руб/сут*\nДезинфекция паром без химии.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("мойщик", "окна", "окон"): "🪟 *Мойщик окон*\n\nСтоимость проката: от *20 руб/сут*\nБыстрая и удобная мойка окон.\n\n📞 Для бронирования: +375 29 738-54-04 (Viber)",
    ("цена", "цены", "стоимость", "сколько", "стоит", "прайс"): "💰 *Цены на прокат:*\n\n🚗 Автокресло — от 15 руб/нед\n🛝 Коляска — от 35 руб/нед\n🛏️ Кроватка — от 20 руб/нед\n🪄 Качели — от 45 руб/нед\n🎪 Манеж — от 20 руб/нед\n🥤 Стульчик — от 20 руб/нед\n🐘 Ходунки — от 20 руб/нед\n🏋️ Прыгунки — от 20 руб/нед\n\nБытовая техника:\n🧹 Пылесос — от 50 руб/сут\n♨️ Пароочиститель — от 35 руб/сут\n🪟 Мойщик окон — от 20 руб/сут",
    ("доставка", "привезти", "доставить"): "🚚 *Доставка*\n\n📦 Малогабаритный товар — через Яндекс доставку\n🛝 Крупногабаритный — самовывоз или по договорённости\n\n📍 Самовывоз: б. Дружбы 4, Автошкола ДОСААФ, 1 этаж\n⏰ Пн–Пт: 17:00–19:00",
    ("залог", "депозит"): "💵 *Залог*\n\nЗалог берётся при оформлении договора и возвращается при возврате товара в целости.\n\n📞 Уточните размер: +375 29 738-54-04 (Viber)",
    ("оплата", "оплатить", "ерип", "безнал", "наличные"): "💳 *Оплата*\n\n✅ Наличный расчёт\n✅ Безналичный расчёт\n✅ Продление договора через ЕРИП",
    ("паспорт", "документы"): "📄 *Документы*\n\nДля заключения договора необходим паспорт гражданина РБ.\n\n📞 Записаться: +375 29 738-54-04 (Viber)",
    ("адрес", "находитесь", "где"): "📍 *Наш адрес*\n\nг. Мозырь, б. Дружбы 4\nТерритория Автошколы ДОСААФ, 1 этаж\n\n⏰ Пн–Пт: 17:00–19:00",
    ("телефон", "позвонить", "номер", "контакт", "связаться"): "📞 *Контакты*\n\n📱 +375 29 738-54-04 (Viber)\n📞 +375 29 120-85-37\n\n💬 Или пишите прямо сюда!",
    ("работаете", "часы", "открыты", "график"): "🕐 *График работы*\n\nПн–Пт: 17:00–19:00\nСуббота: уточняйте по телефону\nВоскресенье: выходной\n\n💬 Написать можно в любое время!",
    ("привет", "здравствуйте", "добрый", "хай"): "👋 Привет! Добро пожаловать в *Bonnybaby*!\n\nВыберите раздел в меню или задайте вопрос.",
    ("спасибо", "благодарю"): "😊 Пожалуйста! Рады помочь!\n\n📱 +375 29 738-54-04 (Viber)",
}

DEFAULT_REPLY = "Спасибо за вопрос! 🙏\n\nДля получения подробной информации свяжитесь с нами:\n📱 +375 29 738-54-04 (Viber)\n📞 +375 29 120-85-37\n\nИли воспользуйтесь меню ниже 👇"


def get_smart_reply(text: str) -> str:
    text_lower = text.lower()
    for keywords, reply in SMART_REPLIES.items():
        for keyword in keywords:
            if keyword in text_lower:
                return reply
    return DEFAULT_REPLY


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Каталог товаров", callback_data="catalog"),
         InlineKeyboardButton("💰 Условия проката", callback_data="conditions")],
        [InlineKeyboardButton("🕐 График работы", callback_data="schedule"),
         InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton("🚚 Доставка", callback_data="delivery"),
         InlineKeyboardButton("❓ Задать вопрос", callback_data="ask")],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
    ])


def catalog_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Автокресло", callback_data="item_seat"),
         InlineKeyboardButton("🛝 Коляска", callback_data="item_stroller")],
        [InlineKeyboardButton("🛏️ Кроватка", callback_data="item_bed"),
         InlineKeyboardButton("🪄 Качели", callback_data="item_swing")],
        [InlineKeyboardButton("🎪 Манеж", callback_data="item_playpen"),
         InlineKeyboardButton("🥤 Стульчик", callback_data="item_chair")],
        [InlineKeyboardButton("🐘 Ходунки", callback_data="item_walker"),
         InlineKeyboardButton("🏋️ Прыгунки", callback_data="item_jumper")],
        [InlineKeyboardButton("🧹 Пылесос", callback_data="item_vacuum"),
         InlineKeyboardButton("♨️ Пароочист.", callback_data="item_steam")],
        [InlineKeyboardButton("🪟 Мойщик окон", callback_data="item_window")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ])


CATALOG_ITEMS = {
    "item_seat":     "🚗 *Автокресло*\n\nНеделя: от *15 руб*\n\nПроверены на безопасность, продезинфицированы.",
    "item_stroller": "🛝 *Коляска прогулочная*\n\nНеделя: от *35 руб*\n\nЛёгкие и манёвренные модели.",
    "item_bed":      "🛏️ *Кроватка с матрасом*\n\nНеделя: от *20 руб*\n\nВ комплекте матрас.",
    "item_swing":    "🪄 *Качели-шезлонг*\n\nНеделя: от *45 руб*\n\nЭлектронные и механические модели.",
    "item_playpen":  "🎪 *Манеж игровой*\n\nНеделя: от *20 руб*\n\nСкладной, с дном.",
    "item_chair":    "🥤 *Стульчик для кормления*\n\nНеделя: от *20 руб*\n\nРегулируемая высота и спинка.",
    "item_walker":   "🐘 *Ходунки*\n\nНеделя: от *20 руб*\n\nДля детей от 6 месяцев.",
    "item_jumper":   "🏋️ *Прыгунки*\n\nНеделя: от *20 руб*\n\nКрепятся на дверной проём.",
    "item_vacuum":   "🧹 *Моющий пылесос*\n\nСутки: от *50 руб*\n\nГлубокая чистка ковров и мягкой мебели.",
    "item_steam":    "♨️ *Пароочиститель*\n\nСутки: от *35 руб*\n\nДезинфекция паром без химии.",
    "item_window":   "🪟 *Мойщик окон*\n\nСутки: от *20 руб*\n\nБыстрая и удобная мойка окон.",
}

TEXT_CONDITIONS = "📋 *Условия проката*\n\n1️⃣ Паспорт гражданина РБ обязателен\n2️⃣ Оплата: наличный или безналичный расчёт\n3️⃣ Продление договора — через ЕРИП\n4️⃣ Все товары дезинфицированы\n5️⃣ Мин. срок — 1 неделя (техника от 1 суток)"
TEXT_SCHEDULE = "🕐 *График работы*\n\nПн–Пт: 17:00 – 19:00\nСуббота: уточняйте по телефону\nВоскресенье: выходной 🏠\n\nНаписать можно в любое время — ответим!"
TEXT_CONTACTS = "📞 *Контакты Bonnybaby*\n\n📍 г. Мозырь, б. Дружбы 4\n(Территория Автошколы ДОСААФ, 1 этаж)\n\n📱 +375 29 738-54-04 (Viber)\n📞 +375 29 120-85-37\n\n💬 Пишите прямо сюда — ответим быстро!"
TEXT_DELIVERY = "🚚 *Доставка*\n\n📦 *Малогабаритный товар* (прыгунки, ходунки, стульчик и др.)\n→ Доставка через Яндекс доставку 🚖\n\n🛝 *Крупногабаритный товар* (коляска, кроватка, манеж и др.)\n→ Самовывоз или по договорённости\n\n📍 Самовывоз: б. Дружбы 4, Автошкола ДОСААФ, 1 этаж\nПн–Пт: 17:00–19:00"
TEXT_WELCOME = "👶 Добро пожаловать в *Bonnybaby*!\nПрокат детских товаров и бытовой техники в Мозыре.\n\nВыберите раздел или задайте вопрос 👇"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXT_WELCOME, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "main_menu":
        await query.edit_message_text(TEXT_WELCOME, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif data == "catalog":
        await query.edit_message_text("🛒 *Каталог товаров*\n\nВыберите товар:", parse_mode="Markdown", reply_markup=catalog_keyboard())
    elif data in CATALOG_ITEMS:
        await query.edit_message_text(CATALOG_ITEMS[data], parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К каталогу", callback_data="catalog"), InlineKeyboardButton("📞 Связаться", callback_data="contacts")]]))
    elif data == "conditions":
        await query.edit_message_text(TEXT_CONDITIONS, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "schedule":
        await query.edit_message_text(TEXT_SCHEDULE, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "contacts":
        await query.edit_message_text(TEXT_CONTACTS, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "delivery":
        await query.edit_message_text(TEXT_DELIVERY, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "ask":
        await query.edit_message_text("❓ *Задайте ваш вопрос*\n\nНапишите сообщение и я отвечу! 👇",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]]))


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    answer = get_smart_reply(user_text)
    await update.message.reply_text(answer, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def main():
    # Запускаем HTTP сервер в отдельном потоке
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    logger.info("HTTP сервер запущен")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Бот Bonnybaby запущен!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
