import logging
import os
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8621586893:AAEDvHWz2zPBYxi7qCD63ZI6_2txPBHe-6g")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-4aa24046ea664d249b96f9ed68cfa781")

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = """Ты — умный менеджер по продажам компании «Красная Печать» из Омска. Вы занимаетесь свадебной полиграфией.

Твоя задача — провести клиента по воронке продаж:

ШАГ 1. Поздоровайся и спроси что нужно клиенту. Узнай какие именно позиции его интересуют:
- Пригласительные
- Карточки рассадки
- Холсты из фотографий
- Бонбоньерки (подарки гостям)
- Или несколько сразу

ШАГ 2. Уточни детали по каждой позиции:
- Количество штук
- Дата свадьбы (чтобы понять срочность)
- Пожелания по стилю и цвету
- Нужен ли индивидуальный дизайн или подойдёт готовый шаблон

ШАГ 3. Рассчитай стоимость исходя из потребностей клиента. Используй эти базовые цены (клиенту их не показывай — только итоговую сумму):
- Пригласительные: от 80 руб/шт, минимальная сумма заказа 2000 руб
- Карточки рассадки: от 40 руб/шт
- Холст 30х40 см: от 1200 руб, 40х60 см: от 1800 руб, Диптих: от 2200 руб
- Бонбоньерки крафт: от 60 руб/шт, атласный мешочек: от 80 руб/шт, тубус: от 95 руб/шт
- Индивидуальный дизайн макета: +1000 руб
Срок изготовления: 5-10 рабочих дней. Доставка по России — СДЭК или Почта России, самовывоз в Омске.

ШАГ 4. Озвучь итоговую стоимость красиво и понятно. Например:
"Для вас получается: 50 пригласительных + карточки рассадки = 6 500 руб. Доставка рассчитывается отдельно по вашему городу."

ШАГ 5. Спроси — всё ли устраивает? Если клиент согласен — скажи что передашь заявку менеджеру, он свяжется в ближайшее время для уточнения деталей и пришлёт ссылку на оплату.

Правила общения:
- Говори дружелюбно, тепло, как живой человек — не как робот
- Не перегружай клиента вопросами — задавай по 1-2 вопроса за раз
- Если клиент сомневается — помоги с выбором, предложи что обычно берут другие пары
- Никогда не показывай прайс списком — только итоговую сумму после выяснения потребностей"""

user_histories = {}

MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("💬 Рассчитать стоимость", callback_data="chat")],
    [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
    [InlineKeyboardButton("🎓 Курс полиграфии на дому", callback_data="course")],
])

BACK = InlineKeyboardMarkup([
    [InlineKeyboardButton("← Назад в меню", callback_data="main")]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "👋 Добро пожаловать в *Красная Печать* — свадебная полиграфия из Омска!\n\n"
        "Мы создаём пригласительные, карточки рассадки, холсты и бонбоньерки для вашего особенного дня.\n\n"
        "Выберите что вас интересует:",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "main":
        user_histories[user_id] = []
        await query.edit_message_text(
            "👋 Добро пожаловать в *Красная Печать* — свадебная полиграфия из Омска!\n\n"
            "Выберите что вас интересует:",
            parse_mode="Markdown",
            reply_markup=MAIN_MENU
        )

    elif data == "chat":
        user_histories[user_id] = []
        await query.edit_message_text(
            "Привет! Давайте подберём всё что нужно для вашей свадьбы и рассчитаем стоимость.\n\n"
            "Расскажите — что вы планируете заказать?",
            reply_markup=BACK
        )

    elif data == "faq":
        await query.edit_message_text(
            "❓ *Частые вопросы*\n\n"
            "*Какой минимальный тираж?*\n"
            "От 1 штуки. Минимальная сумма заказа — 2 000 руб.\n\n"
            "*Сколько времени занимает изготовление?*\n"
            "5-10 рабочих дней после согласования макета.\n\n"
            "*Можно ли внести правки в дизайн?*\n"
            "Да, правки вносим до полного согласования — всё обсуждаем с вами.\n\n"
            "*Как происходит доставка?*\n"
            "Доставляем по всей России через СДЭК и Почту России. "
            "Самовывоз тоже доступен — мы находимся в Омске.\n\n"
            "*Можно ли заказать индивидуальный дизайн?*\n"
            "Конечно! Разработка индивидуального макета — 1 000 руб.\n\n"
            "*Как оплатить заказ?*\n"
            "После согласования заказа мы пришлём вам ссылку на оплату.",
            parse_mode="Markdown",
            reply_markup=BACK
        )

    elif data == "course":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 9 900 руб", url="https://yoomoney.ru/to/ВСТАВЬ_КОШЕЛЁК")],
            [InlineKeyboardButton("← Назад", callback_data="main")],
        ])
        await query.edit_message_text(
            "🖨 *Обучение заработку на свадебной полиграфии — не выходя из дома!*\n\n"
            "📌 Мы обучаем зарабатывать на свадебной полиграфии не выходя из дома — с нуля до первых заказов!\n\n"
            "🎓 *Что входит в курс:*\n\n"
            "✅ Основы полиграфии — материалы, печать, отделка, оборудование и его обслуживание\n"
            "✅ Урок по работе в CorelDraw от нашего дизайнера\n"
            "✅ База дизайнов и шаблонов пригласительных — 10 готовых шаблонов\n"
            "✅ База шрифтов\n"
            "✅ Отдельный урок по изготовлению пригласительных — как сделать всё аккуратно, красиво и эстетично\n"
            "✅ *Урок по продажам* — самый главный! Как зарабатывать на пригласительных, кому и как продавать, как формировать цену и многое другое\n\n"
            "💡 *Бонус!* При оплате в течение 24 часов — личная консультация на 30 минут!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})

    await update.message.chat.send_action("typing")

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id],
            max_tokens=1000
        )
        reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(
            reply,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("← В меню", callback_data="main")]
            ])
        )
    except Exception as e:
        logging.error(f"API error: {e}")
        await update.message.reply_text(
            "Упс, что-то пошло не так. Попробуйте ещё раз или вернитесь в меню.",
            reply_markup=BACK
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
