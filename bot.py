import logging
import os
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8621586893:AAEDvHWz2zPBYxi7qCD63ZI6_2txPBHe-6g")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-95303a3c9500400db42c3d3caf559387")
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "390540012:LIVE:94857")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "8143913122")

ai_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

SYSTEM_PROMPT = """Твоё имя — Дима. Ты — ИИ-помощник компании «Красная Печать» из Омска. Вы занимаетесь свадебной полиграфией.

Твоя задача — провести клиента по воронке продаж:

ШАГ 1. Поздоровайся, представься что тебя зовут Дима и ты ИИ-помощник компании «Красная Печать», и спроси что нужно клиенту:
- Пригласительные
- Карточки рассадки
- Холсты из фотографий
- Бонбоньерки

ШАГ 2. Уточни детали: количество, дата свадьбы, стиль, нужен ли индивидуальный дизайн.
Если клиент скидывает фото или говорит о конкретном дизайне — скажи что уточняешь стоимость у менеджера и напиши в конце:
СПРОСИ_ХОЗЯИНА: <что именно хочет клиент и сколько штук>

ШАГ 3. Когда хозяин сообщит цену через "ЦЕНА: 5000" — используй её и озвучь клиенту итог.

ШАГ 4. Когда клиент согласен — напиши в конце:
ИТОГ: <сумма цифрами>
СОСТАВ: <краткое описание>

Базовые цены (только для стандарта без инд. дизайна):
- Карточки рассадки: от 40 руб/шт
- Холст 30х40: от 1200 руб, 40х60: от 1800 руб, Диптих: от 2200 руб
- Бонбоньерки крафт: от 60 руб/шт, мешочек: от 80 руб/шт, тубус: от 95 руб/шт
Минимальная сумма: 2000 руб. Срок: 5-10 рабочих дней.

Правила:
- Говори дружелюбно и тепло
- Задавай по 1-2 вопроса за раз
- Цену на пригласительные — только через хозяина
- Никогда не показывай прайс списком"""

user_histories = {}
reminders = {}

MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("💬 Рассчитать стоимость", callback_data="chat")],
    [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
    [InlineKeyboardButton("🎓 Курс полиграфии на дому", callback_data="course")],
    [InlineKeyboardButton("📞 Связаться с менеджером", callback_data="manager")],
])

BACK = InlineKeyboardMarkup([[InlineKeyboardButton("← Назад в меню", callback_data="main")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    username = update.effective_user.username or ""
    user_histories[user_id] = []

    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=f"👤 Новый клиент!\n\nИмя: {name}\nUsername: @{username}\nID: {user_id}"
    )
    await update.message.reply_text(
        "Привет! Меня зовут Дима — я ИИ-помощник компании «Красная Печать» 🤖\n\n"
        "Помогу подобрать свадебную полиграфию и рассчитаю стоимость. "
        "Если понадобится живой менеджер — сразу передам!"
    )
    await update.message.reply_text("Вот что я умею — выбирайте:", reply_markup=MAIN_MENU)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "main":
        user_histories[user_id] = []
        await query.edit_message_text("Вот что я умею — выбирайте:", reply_markup=MAIN_MENU)

    elif data == "chat":
        user_histories[user_id] = []
        await query.edit_message_text(
            "Отлично! Давайте подберём всё что нужно для вашей свадьбы.\n\nНапишите что вас интересует 👇",
            reply_markup=BACK
        )

    elif data == "manager":
        await query.edit_message_text(
            "📞 Связаться с менеджером\n\nНапишите нам напрямую — ответим в ближайшее время!\n\n👉 @Redstamp_bot",
            reply_markup=BACK
        )

    elif data == "faq":
        await query.edit_message_text(
            "❓ Частые вопросы\n\n"
            "Какой минимальный тираж?\nОт 1 штуки. Минимальная сумма — 2 000 руб.\n\n"
            "Сколько времени занимает изготовление?\n5-10 рабочих дней после согласования макета.\n\n"
            "Можно ли внести правки в дизайн?\nДа, до полного согласования.\n\n"
            "Как происходит доставка?\nСДЭК и Почта России. Самовывоз в Омске.\n\n"
            "Можно ли заказать индивидуальный дизайн?\nКонечно! Разработка макета — 1 000 руб.\n\n"
            "Как оплатить заказ?\nПришлём счёт прямо в этот чат.",
            reply_markup=BACK
        )

    elif data == "course":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 9 900 руб", callback_data="pay_course")],
            [InlineKeyboardButton("← Назад", callback_data="main")],
        ])
        await query.edit_message_text(
            "🖨 Обучение заработку на свадебной полиграфии — не выходя из дома!\n\n"
            "📌 С нуля до первых заказов!\n\n"
            "Что входит:\n"
            "✅ Основы полиграфии — материалы, печать, отделка, оборудование\n"
            "✅ Урок по CorelDraw от нашего дизайнера\n"
            "✅ 10 готовых шаблонов пригласительных\n"
            "✅ База шрифтов\n"
            "✅ Урок по изготовлению — аккуратно и эстетично\n"
            "✅ Урок по продажам — как зарабатывать, кому и как продавать\n\n"
            "Бонус! Оплата в течение 24 часов — консультация на 30 минут!",
            reply_markup=keyboard
        )

    elif data == "pay_course":
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="Курс «Полиграфия на дому»",
            description="Обучение заработку на свадебной полиграфии не выходя из дома.",
            payload="course_payment",
            provider_token=PAYMENT_TOKEN,
            currency="RUB",
            prices=[LabeledPrice("Курс «Полиграфия на дому»", 990000)],
            need_name=True, need_phone_number=True,
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    username = update.effective_user.username or ""
    text = update.message.text
    chat_id = str(update.message.chat_id)

    # Сообщение от хозяина с ценой
    if chat_id == OWNER_CHAT_ID and text.startswith("ЦЕНА:"):
        parts = text.split()
        try:
            price = int("".join(filter(str.isdigit, parts[1])))
            client_id = None
            for i, p in enumerate(parts):
                if "клиент" in p.lower() and i + 1 < len(parts):
                    client_id = int(parts[i + 1])
            if client_id and client_id in user_histories:
                user_histories[client_id].append({
                    "role": "user",
                    "content": f"[ОТ ХОЗЯИНА]: Цена — {price} руб. Озвучь клиенту итоговую сумму."
                })
                response = await ai_client.chat.completions.create(
                    model="deepseek-chat",
                    max_tokens=500,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[client_id]
                )
                reply = response.choices[0].message.content
                user_histories[client_id].append({"role": "assistant", "content": reply})
                await context.bot.send_message(chat_id=client_id, text=reply)
                reminders[client_id] = {"send_at": datetime.now() + timedelta(hours=24), "type": "followup"}
                await update.message.reply_text(f"✅ Цена передана клиенту {client_id}")
            else:
                await update.message.reply_text("Не нашёл клиента. Формат: ЦЕНА: 5000 клиент: 123456789")
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("Ошибка. Формат: ЦЕНА: 5000 клиент: 123456789")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})
    await update.message.chat.send_action("typing")

    try:
        response = await ai_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=1000,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
        )
        reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if "СПРОСИ_ХОЗЯИНА:" in reply:
            lines = reply.split("\n")
            clean_reply, question = "", ""
            for line in lines:
                if line.startswith("СПРОСИ_ХОЗЯИНА:"):
                    question = line.replace("СПРОСИ_ХОЗЯИНА:", "").strip()
                else:
                    clean_reply += line + "\n"
            await update.message.reply_text(clean_reply.strip())
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"Запрос цены!\n\nКлиент: {name} (@{username}, id: {user_id})\n\n{question}\n\nОтветь:\nЦЕНА: 5000 клиент: {user_id}"
            )

        elif "ИТОГ:" in reply and "СОСТАВ:" in reply:
            lines = reply.split("\n")
            amount, description, clean_reply = None, "Заказ свадебной полиграфии", ""
            for line in lines:
                if line.startswith("ИТОГ:"):
                    try:
                        amount = int("".join(filter(str.isdigit, line)))
                    except:
                        pass
                elif line.startswith("СОСТАВ:"):
                    description = line.replace("СОСТАВ:", "").strip()
                else:
                    clean_reply += line + "\n"
            await update.message.reply_text(clean_reply.strip())
            if amount and amount >= 100:
                reminders.pop(user_id, None)
                await context.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=f"📋 Новый заказ!\n\nКлиент: {name} (@{username}, id: {user_id})\nСостав: {description}\nСумма: {amount} руб\n\nОтправляю счёт клиенту..."
                )
                await context.bot.send_invoice(
                    chat_id=update.message.chat_id,
                    title="Заказ — Красная Печать",
                    description=description,
                    payload=f"order_{user_id}",
                    provider_token=PAYMENT_TOKEN,
                    currency="RUB",
                    prices=[LabeledPrice("Оплата заказа 100%", amount * 100)],
                    need_name=True, need_phone_number=True,
                )
        else:
            await update.message.reply_text(
                reply,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← В меню", callback_data="main")]])
            )

    except Exception as e:
        logging.error(f"API error: {e}")
        await update.message.reply_text("Что-то пошло не так. Попробуйте ещё раз.", reply_markup=BACK)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc:
        await update.message.reply_text(f"file_id: {doc.file_id}")

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    username = update.effective_user.username or ""
    amount = payment.total_amount // 100
    charge_id = payment.provider_payment_charge_id

    reminders.pop(user_id, None)
    reminders[user_id] = {"send_at": datetime.now() + timedelta(hours=336), "type": "review"}

    await update.message.reply_text(
        f"✅ Оплата {amount} руб получена!\n\nСпасибо! Менеджер свяжется с вами в ближайшее время.",
        reply_markup=MAIN_MENU
    )
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=f"💰 Новая оплата!\n\nКлиент: {name} (@{username}, id: {user_id})\nСумма: {amount} руб\nID транзакции: {charge_id}"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != OWNER_CHAT_ID:
        return
    total = len(user_histories)
    await update.message.reply_text(f"📊 Статистика\n\nАктивных диалогов: {total}")

async def check_reminders(context):
    now = datetime.now()
    to_delete = []
    for user_id, data in list(reminders.items()):
        if now >= data["send_at"]:
            to_delete.append(user_id)
            try:
                if data["type"] == "followup":
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Привет! Это снова Дима из «Красной Печати» 😊\n\nХотел уточнить — вы ещё думаете над заказом? Если остались вопросы — с удовольствием отвечу!",
                        reply_markup=MAIN_MENU
                    )
                elif data["type"] == "review":
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Привет! Это Дима из «Красной Печати» 😊\n\nПрошло две недели — как вам наша работа? Будем очень рады отзыву! 🙏"
                    )
            except Exception as e:
                logging.error(f"Reminder error for {user_id}: {e}")
    for uid in to_delete:
        reminders.pop(uid, None)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_reminders, interval=3600, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
