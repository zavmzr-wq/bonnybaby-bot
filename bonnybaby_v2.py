import logging
import os
import asyncio
import httpx
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

TELEGRAM_TOKEN = "8789819533:AAESS2xsCpwJkniX7jq3oRggcOBF3AhDYG4"
GEMINI_API_KEY = "AQ.Ab8RN6KHHnj-ZEIo73N_VxG8hey0-3tUKHx-Ky24bfggSvJYwg"

SYSTEM_PROMPT = """Ты — вежливый помощник пункта проката детских товаров и бытовой техники «Bonnybaby» в Мозыре (Беларусь).
Отвечай кратко (2-4 предложения), дружелюбно, на русском языке. Используй эмодзи умеренно.

КАТАЛОГ (прокат):
Автокресло — от 15 руб/нед
Коляска — от 35 руб/нед
Кроватка — от 20 руб/нед
Качели — от 45 руб/нед
Манеж — от 20 руб/нед
Стульчик для кормления — от 20 руб/нед
Ходунки — от 20 руб/нед
Прыгунки — от 20 руб/нед
Моющий пылесос — от 50 руб/сут
Пароочиститель — от 35 руб/сут
Мойщик окон — от 20 руб/сут

КОНТАКТЫ:
Адрес: г. Мозырь, б. Дружбы 4 (Территория Автошколы ДОСААФ, 1 этаж)
Тел: +375 29 738-54-04 (Viber)
Тел: +375 29 120-85-37

ГРАФИК РАБОТЫ:
Пн-Пт: 17:00-19:00
Суббота: уточняйте по телефону
Воскресенье: выходной

ДОСТАВКА:
Малогабаритный товар (прыгунки, ходунки, стульчик и др.) — через Яндекс доставку.
Крупногабаритный — самовывоз или по договорённости.

УСЛОВИЯ:
- Паспорт гражданина РБ обязателен для договора
- Оплата: наличный или безналичный расчёт
- Продление договора — через ЕРИП
- Все товары дезинфицированы
- Минимальный срок аренды: 1 неделя (техника — от 1 суток)"""


async def get_ai_response(user_text: str, history: list) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


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

TEXT_CONDITIONS = (
    "📋 *Условия проката*\n\n"
    "1️⃣ Паспорт гражданина РБ обязателен\n"
    "2️⃣ Оплата: наличный или безналичный расчёт\n"
    "3️⃣ Продление договора — через ЕРИП\n"
    "4️⃣ Все товары дезинфицированы\n"
    "5️⃣ Мин. срок — 1 неделя (техника от 1 суток)"
)
TEXT_SCHEDULE = (
    "🕐 *График работы*\n\n"
    "Пн–Пт: 17:00 – 19:00\n"
    "Суббота: уточняйте по телефону\n"
    "Воскресенье: выходной 🏠\n\n"
    "Написать можно в любое время — ответим!"
)
TEXT_CONTACTS = (
    "📞 *Контакты Bonnybaby*\n\n"
    "📍 г. Мозырь, б. Дружбы 4\n"
    "(Территория Автошколы ДОСААФ, 1 этаж)\n\n"
    "📱 +375 29 738-54-04 (Viber)\n"
    "📞 +375 29 120-85-37\n\n"
    "💬 Пишите прямо сюда — ответим быстро!"
)
TEXT_DELIVERY = (
    "🚚 *Доставка*\n\n"
    "📦 *Малогабаритный товар* (прыгунки, ходунки, стульчик и др.)\n"
    "→ Доставка через Яндекс доставку 🚖\n\n"
    "🛝 *Крупногабаритный товар* (коляска, кроватка, манеж и др.)\n"
    "→ Самовывоз или по договорённости\n\n"
    "📍 Самовывоз: б. Дружбы 4, Автошкола ДОСААФ, 1 этаж\n"
    "Пн–Пт: 17:00–19:00"
)
TEXT_WELCOME = (
    "👶 Добро пожаловать в *Bonnybaby*!\n"
    "Прокат детских товаров и бытовой техники в Мозыре.\n\n"
    "Выберите раздел или задайте вопрос 👇"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text(
        TEXT_WELCOME, parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(TEXT_WELCOME, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif data == "catalog":
        await query.edit_message_text("🛒 *Каталог товаров*\n\nВыберите товар:", parse_mode="Markdown", reply_markup=catalog_keyboard())
    elif data in CATALOG_ITEMS:
        await query.edit_message_text(
            CATALOG_ITEMS[data], parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К каталогу", callback_data="catalog"),
                 InlineKeyboardButton("📞 Связаться", callback_data="contacts")],
            ]),
        )
    elif data == "conditions":
        await query.edit_message_text(TEXT_CONDITIONS, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "schedule":
        await query.edit_message_text(TEXT_SCHEDULE, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "contacts":
        await query.edit_message_text(TEXT_CONTACTS, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "delivery":
        await query.edit_message_text(TEXT_DELIVERY, parse_mode="Markdown", reply_markup=back_keyboard())
    elif data == "ask":
        await query.edit_message_text(
            "❓ *Задайте ваш вопрос*\n\nНапишите сообщение — отвечу на любой вопрос о прокате 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]]),
        )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    history = context.user_data.get("history", [])
    await update.message.chat.send_action("typing")
    try:
        answer = await get_ai_response(user_text, history)
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        answer = "Извините, не могу ответить прямо сейчас 😔\nПозвоните: 📱 +375 29 738-54-04 (Viber)"
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": answer})
    context.user_data["history"] = history[-10:]
    await update.message.reply_text(
        answer,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Главное меню", callback_data="main_menu")]]),
    )


async def main():
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
