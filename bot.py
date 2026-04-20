import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("BOT_TOKEN", "8621586893:AAEDvHWz2zPBYxi7qCD63ZI6_2txPBHe-6g")

MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 Прайс", callback_data="price")],
    [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
    [InlineKeyboardButton("🎓 Курс полиграфии на дому", callback_data="course")],
    [InlineKeyboardButton("📞 Связаться с нами", callback_data="contact")],
])

BACK = InlineKeyboardMarkup([
    [InlineKeyboardButton("← Назад", callback_data="main")]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в *Красная Печать* — свадебная полиграфия!\n\n"
        "Мы делаем пригласительные, карточки рассадки, холсты и бонбоньерки "
        "для вашего особенного дня.\n\n"
        "Выберите что вас интересует:",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main":
        await query.edit_message_text(
            "👋 Добро пожаловать в *Красная Печать* — свадебная полиграфия!\n\n"
            "Мы делаем пригласительные, карточки рассадки, холсты и бонбоньерки "
            "для вашего особенного дня.\n\n"
            "Выберите что вас интересует:",
            parse_mode="Markdown",
            reply_markup=MAIN_MENU
        )

    elif data == "price":
        await query.edit_message_text(
            "📋 *Наш прайс*\n\n"
            "✉️ *Свадебные пригласительные*\n"
            "от 80 ₽ / шт\n\n"
            "🪑 *Карточки рассадки*\n"
            "от 40 ₽ / шт\n\n"
            "🖼 *Холст из вашей фотографии*\n"
            "30×40 см — от 1 200 ₽\n"
            "40×60 см — от 1 800 ₽\n"
            "Диптих — от 2 200 ₽\n\n"
            "🎁 *Бонбоньерки*\n"
            "Крафт-коробочка — от 60 ₽ / шт\n"
            "Атласный мешочек — от 80 ₽ / шт\n"
            "Тубус с лентой — от 95 ₽ / шт\n\n"
            "_Точная стоимость зависит от тиража и дизайна. "
            "Напишите нам для расчёта!_",
            parse_mode="Markdown",
            reply_markup=BACK
        )

    elif data == "faq":
        await query.edit_message_text(
            "❓ *Частые вопросы*\n\n"
            "*Какой минимальный тираж?*\n"
            "От 20 штук для пригласительных и карточек рассадки.\n\n"
            "*Сколько времени занимает изготовление?*\n"
            "Обычно 5–7 рабочих дней после согласования макета.\n\n"
            "*Можно ли внести правки в дизайн?*\n"
            "Да, мы делаем до 3 правок бесплатно.\n\n"
            "*Как происходит доставка?*\n"
            "Доставляем по всей России через СДЭК и Почту России. "
            "Самовывоз тоже доступен.\n\n"
            "*Можно ли заказать индивидуальный дизайн?*\n"
            "Конечно! Разработка индивидуального макета — от 500 ₽.\n\n"
            "*Как оплатить заказ?*\n"
            "Принимаем оплату через ЮМани, перевод на карту. "
            "Предоплата 50% при подтверждении заказа.",
            parse_mode="Markdown",
            reply_markup=BACK
        )

    elif data == "course":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 9 900 ₽", url="https://yoomoney.ru/to/ВСТАВЬ_КОШЕЛЁК")],
            [InlineKeyboardButton("← Назад", callback_data="main")],
        ])
        await query.edit_message_text(
            "🖨 *Красная Печать — обучение полиграфии на дому!*\n\n"
            "📌 Научись делать свадебную полиграфию профессионально — не выходя из дома!\n\n"
            "🎓 *Курс «Полиграфия на дому»* — всё что нужно чтобы начать зарабатывать на свадебной печати\n\n"
            "Что входит в курс?\n"
            "✅ Основы полиграфии — материалы, печать, отделка\n"
            "✅ Пригласительные, карточки рассадки, бонбоньерки\n"
            "✅ Работа с макетами и шаблонами\n"
            "✅ Где закупать материалы по оптовым ценам\n"
            "✅ Как находить клиентов и выстраивать продажи\n"
            "✅ Разбор реальных заказов с куратором\n\n"
            "💡 *Бонус!* При оплате в течение 24 часов — личная консультация на 30 минут!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif data == "contact":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✈️ Написать менеджеру", url="https://t.me/Redstamp_bot")],
            [InlineKeyboardButton("← Назад", callback_data="main")],
        ])
        await query.edit_message_text(
            "📞 *Связаться с нами*\n\n"
            "Готовы ответить на любые вопросы и помочь с выбором!\n\n"
            "Напишите нам — и мы рассчитаем стоимость вашего заказа в течение нескольких часов.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
