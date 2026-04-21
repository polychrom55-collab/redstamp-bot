import logging
import os
import json
import asyncio
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8621586893:AAEDvHWz2zPBYxi7qCD63ZI6_2txPBHe-6g")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-95303a3c9500400db42c3d3caf559387")
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "390540012:LIVE:94857")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "8143913122")
SHEET_ID = os.environ.get("SHEET_ID", "1CGIKc4wW59NS6zS2dmgt17r7cMoTTU3Op8yZ2c0BkMc")

GOOGLE_CREDS = {
    "type": "service_account",
    "project_id": "eng-throne-494008-c3",
    "private_key_id": "670c87f40d5c3c2ded2046e5bf4bd175495f659b",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDTArvu0Tes9MWR\nmf9IR1feUeuyEGj9wf6d8l30a7scadVtqLK7zc7VGLcRJ52CPoCQTojeon9WSJqF\nB6IfXINQNkr+6YOY3ih8tUaC/h6zDoB5TBn2rxoVdQ2b23EuBD41Qw5XkLQ+jQJ1\nO3MkXLUNXnnNjaKgbLWIgtztqaemdMId8/a2dMSlcOVWlNYDI/rnJauVcgDlav5+\n/gwbNglZ1cynwIPKAsj4GFeu16QwUo+vW9AAZ4woNbciru6vj1fvFyk6zaSqBF5K\n8UN/s8gYyFDZumrNS7UzZcJtd1iaQpBPRu8bIo1qF3yq3UHMNkAjEJOxy1OOAdXO\nSvR17XMbAgMBAAECggEAXZji38Xx2kggsrsKX3c15KmV0MAysgyw8kKlplt6/dl8\nEE46Kc/apO93lKZr2W/7+wa683ZE4XMHB2chZKPWo2fR0EyoUNCKSPbntgceevI9\nzpARHDkDau0nAjFOfMjpBxsda34GVZCavIGIS2LL9IgpoyHmNx7BTzIs6UbN1Kk7\niCbDoeXkvkLyf/dpByO+2ljh5b2FIHLT+bhR6/H0x47yEqpZ1TRSL9/I+voqB3Hg\nVlRRI7atcHx7K5f2ILMJDFa+d2nlxp2Ny+1p1eOXjquK3YCuoGIvY6fjUlKfbeYZ\noL4U9cxUSQsEgQL5evM6cPXNVEIkpi8fN2KSwgb4gQKBgQDuYIQAWjKvVG9q7+Bx\noC2xHuByW6tYCDkeZAWPJLRogW1z+J1tNNxn+y0aa5YPVWwncuJe6xeSnpeQBNER\n6qpt5Q/NiY2/qmeaUAAhMPwkF9Jow8YP7kgMrGlXQp1rqPqI41YxkMiu8K7LO/gX\n851Fue64mUJ0SMMk8/bF7OYG+wKBgQDinEmoHn6lxir8BbZoqV7jzd+hrk52lIaA\nIQ/hguFdRRSDbvhtDA03OgR4gUcjYVIXx6BRSsk6ToKplzC2+/Dtoz47bLKqbo92\n4GgXjWNi9TiKE+pZjvUlwTPEQBe2g8mgiebuyVcV46MVQvBF0M55IdEC3VxbYk7L\nSPSvR00KYQKBgHW5eLdr1Eg+nN/lI6U6BBbLNvGDUDWjqgHWR+CPsgFCmjmB+M1s\nI8W+iGHZ7DwaZdV9qUpTNEsWw6c+mboNeKnZTFqnqjeUAqJ1C/tYY823bhSLSw+n\nEDIiG8wafAAlbcWY8IJ+DH5JIyn/reC2UV+UGc9U8TrYjHd9fMv22QttAoGBAIMm\nInbbFz8H3o63G6edBl7fImMnRx/Xu7Ph7pf8MEPTnBipG7u4stlYiYfYgfxW8bTz\ngrQpjSZik7pk1vu/+eL+jCDGOuzqSbtqCrQ+zttRwqQe/I1ScEymcThOQ6sMwJ9Z\n0D44Zl8zvImskPRG8Ygnaxi2ViJJVgLOuVXL9SlhAoGAQGm//dqri0ZSLW2JQqTv\n0NK818CYaUa+Wl7SfCXKtFeybO0k86sIIf/VvARY3Axu/wVGX7t4CuOeqJh/Z+7F\n8PLT7gK6EIez1knbT1/Dh05fSJHm+eT2jhk7pdrEFDFVVZBi1r5+6tUM0UwZ2Oqo\n/bUscUfVkQjCIGjXCIM7dss=\n-----END PRIVATE KEY-----\n",
    "client_email": "bot-873@eng-throne-494008-c3.iam.gserviceaccount.com",
    "client_id": "115843652556522334362",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/bot-873%40eng-throne-494008-c3.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# --- Google Sheets ---
def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh

def init_sheets():
    try:
        sh = get_sheet()
        # Лист клиентов
        try:
            ws = sh.worksheet("Клиенты")
        except:
            ws = sh.add_worksheet("Клиенты", rows=1000, cols=10)
            ws.append_row(["ID", "Имя", "Username", "Первый визит", "Последний визит"])
        # Лист заказов
        try:
            ws2 = sh.worksheet("Заказы")
        except:
            ws2 = sh.add_worksheet("Заказы", rows=1000, cols=10)
            ws2.append_row(["Дата", "ID клиента", "Имя", "Username", "Состав заказа", "Сумма", "Оплачен", "ID транзакции"])
    except Exception as e:
        logging.error(f"Sheets init error: {e}")

def save_client(user_id, name, username):
    try:
        sh = get_sheet()
        ws = sh.worksheet("Клиенты")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        records = ws.get_all_values()
        for i, row in enumerate(records[1:], start=2):
            if row and str(row[0]) == str(user_id):
                ws.update_cell(i, 5, now)
                return
        ws.append_row([user_id, name, username, now, now])
    except Exception as e:
        logging.error(f"save_client error: {e}")

def save_order(user_id, name, username, description, amount):
    try:
        sh = get_sheet()
        ws = sh.worksheet("Заказы")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        ws.append_row([now, user_id, name, username, description, amount, "Нет", ""])
    except Exception as e:
        logging.error(f"save_order error: {e}")

def mark_paid(user_id, charge_id):
    try:
        sh = get_sheet()
        ws = sh.worksheet("Заказы")
        records = ws.get_all_values()
        for i, row in enumerate(records[1:], start=2):
            if row and str(row[1]) == str(user_id) and row[6] == "Нет":
                ws.update_cell(i, 7, "Да")
                ws.update_cell(i, 8, charge_id)
                break
    except Exception as e:
        logging.error(f"mark_paid error: {e}")

def get_stats():
    try:
        sh = get_sheet()
        ws_clients = sh.worksheet("Клиенты")
        ws_orders = sh.worksheet("Заказы")
        today = datetime.now().strftime("%d.%m.%Y")
        clients = ws_clients.get_all_values()[1:]
        orders = ws_orders.get_all_values()[1:]
        today_clients = sum(1 for r in clients if r and today in r[3])
        total_clients = len(clients)
        paid_orders = [r for r in orders if r and r[6] == "Да"]
        paid_sum = sum(int(r[5]) for r in paid_orders if r[5].isdigit())
        pending = sum(1 for r in orders if r and r[6] == "Нет")
        return today_clients, total_clients, len(paid_orders), paid_sum, pending
    except Exception as e:
        logging.error(f"get_stats error: {e}")
        return 0, 0, 0, 0, 0

init_sheets()

# --- Напоминалки в памяти ---
reminders = {}  # user_id -> {"send_at": datetime, "type": "followup"|"review"}

def set_reminder(user_id, hours, reminder_type):
    reminders[user_id] = {
        "send_at": datetime.now() + timedelta(hours=hours),
        "type": reminder_type
    }

def cancel_reminder(user_id):
    reminders.pop(user_id, None)

# --- AI клиент ---
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
    save_client(user_id, name, username)
    user_histories[user_id] = []
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=f"👤 *Новый клиент!*\n\nИмя: {name}\nUsername: @{username}\nID: {user_id}",
        parse_mode="Markdown"
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
            "📞 *Связаться с менеджером*\n\nНапишите нам напрямую — ответим в ближайшее время!\n\n👉 @Redstamp_bot",
            parse_mode="Markdown", reply_markup=BACK
        )

    elif data == "faq":
        await query.edit_message_text(
            "❓ *Частые вопросы*\n\n"
            "*Какой минимальный тираж?*\nОт 1 штуки. Минимальная сумма — 2 000 руб.\n\n"
            "*Сколько времени занимает изготовление?*\n5-10 рабочих дней после согласования макета.\n\n"
            "*Можно ли внести правки в дизайн?*\nДа, до полного согласования.\n\n"
            "*Как происходит доставка?*\nСДЭК и Почта России. Самовывоз в Омске.\n\n"
            "*Можно ли заказать индивидуальный дизайн?*\nКонечно! Разработка макета — 1 000 руб.\n\n"
            "*Как оплатить заказ?*\nПришлём счёт прямо в этот чат.",
            parse_mode="Markdown", reply_markup=BACK
        )

    elif data == "course":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 9 900 руб", callback_data="pay_course")],
            [InlineKeyboardButton("← Назад", callback_data="main")],
        ])
        await query.edit_message_text(
            "🖨 *Обучение заработку на свадебной полиграфии — не выходя из дома!*\n\n"
            "📌 С нуля до первых заказов!\n\n"
            "🎓 *Что входит:*\n"
            "✅ Основы полиграфии — материалы, печать, отделка, оборудование\n"
            "✅ Урок по CorelDraw от нашего дизайнера\n"
            "✅ 10 готовых шаблонов пригласительных\n"
            "✅ База шрифтов\n"
            "✅ Урок по изготовлению — аккуратно и эстетично\n"
            "✅ *Урок по продажам* — как зарабатывать, кому и как продавать\n\n"
            "💡 *Бонус!* Оплата в течение 24 часов — консультация на 30 минут!",
            parse_mode="Markdown", reply_markup=keyboard
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
                set_reminder(client_id, 24, "followup")
                await update.message.reply_text(f"✅ Цена передана клиенту {client_id}")
            else:
                await update.message.reply_text("Не нашёл клиента. Формат: ЦЕНА: 5000 клиент: 123456789")
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("Ошибка. Формат: ЦЕНА: 5000 клиент: 123456789")
        return

    # Обычный клиент
    save_client(user_id, name, username)
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})
    await update.message.chat.send_action("typing")

    try:
        reply = ""
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
                text=f"❗️ *Запрос цены*\n\n👤 {name} (@{username}, id: {user_id})\n\n📋 {question}\n\nОтветь:\n`ЦЕНА: 5000 клиент: {user_id}`",
                parse_mode="Markdown"
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
                save_order(user_id, name, username, description, amount)
                cancel_reminder(user_id)
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

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    username = update.effective_user.username or ""
    amount = payment.total_amount // 100
    charge_id = payment.provider_payment_charge_id

    mark_paid(user_id, charge_id)
    cancel_reminder(user_id)
    set_reminder(user_id, 336, "review")  # отзыв через 2 недели

    await update.message.reply_text(
        f"✅ Оплата {amount} руб получена!\n\nСпасибо! Менеджер свяжется с вами в ближайшее время.",
        reply_markup=MAIN_MENU
    )
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=f"💰 *Новая оплата!*\n\n👤 {name} (@{username}, id: {user_id})\n💵 {amount} руб\n🔖 {charge_id}",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != OWNER_CHAT_ID:
        return
    today_users, total_users, paid_count, paid_sum, pending = get_stats()
    await update.message.reply_text(
        f"📊 *Статистика*\n\n"
        f"👤 Сегодня новых: {today_users}\n"
        f"👥 Всего клиентов: {total_users}\n"
        f"💰 Оплачено заказов: {paid_count}\n"
        f"💵 Общая сумма: {paid_sum} руб\n"
        f"⏳ Ожидают оплаты: {pending}",
        parse_mode="Markdown"
    )

async def check_reminders(context):
    now = datetime.now()
    to_delete = []
    for user_id, data in reminders.items():
        if now >= data["send_at"]:
            to_delete.append(user_id)
            try:
                if data["type"] == "followup":
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Привет! Это снова Дима из «Красной Печати» 😊\n\n"
                             "Хотел уточнить — вы ещё думаете над заказом? "
                             "Если остались вопросы — с удовольствием отвечу!",
                        reply_markup=MAIN_MENU
                    )
                elif data["type"] == "review":
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Привет! Это Дима из «Красной Печати» 😊\n\n"
                             "Прошло две недели — как вам наша работа? "
                             "Будем очень рады отзыву — это помогает нам становиться лучше! 🙏"
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
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_reminders, interval=3600, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
