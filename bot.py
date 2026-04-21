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

PRICE_LIST_FILE_ID = "BQACAgIAAxkBAAOkaedhHLLHMb_XGt9oO9sVn3IZWnAAAl6bAAJAuzlLg2SzJGD-hFs7BA"

PRICE_PAGES = [
    "AgACAgIAAxkDAAOyaedj0az_RWpDxsGhOQ8F7OYoriMAAmIUaxtAuzlLN7yRe3tum0ABAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAOzaedj0yEs41Wp0LUd6rryO_CiQ3cAAmMUaxtAuzlLSoarKtlHMwEBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO0aedj1Pc7e845YGZZZHQFcQ1UhdYAAmQUaxtAuzlLeY2TC1_6DgYBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO1aedj1gQGKjwenqs6sWYJKPUqcT0AAmUUaxtAuzlLxFh1g-LpEdUBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO2aedj13ocTYINLtSGRpCGot8TyQ4AAmYUaxtAuzlLyAaxmXEaBuwBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO3aedj2G_6zbtArZVi62_-BL-ozhMAAmcUaxtAuzlL5PsIet0R8lwBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO4aedj2isSPIpHjgOI0CSzolfbAb8AAmgUaxtAuzlLK9SpBkz-ofcBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO5aedj3IW1dmJsRfmm2iQeDlTrneAAAmkUaxtAuzlLrYKwyvosnBYBAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO6aedj3e9Q2K0fGcr3xQjFUFGFsHgAAmoUaxtAuzlLBTlk3-nQml4BAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO7aedj3raz97YtNZDvkjeIwzJA0x0AAmsUaxtAuzlLrAvuxPnQyU4BAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO8aedj4CwM954b5pfYwsaXbuVf2BIAAmwUaxtAuzlLfLhwtrRCGD4BAAMCAAN5AAM7BA",
    "AgACAgIAAxkDAAO9aedj4Q52FhIt-97qiutBli4eSosAAm4UaxtAuzlLfA8fhhDQa4QBAAMCAAN5AAM7BA",
]

# Названия наборов
PRICE_NAMES = [
    "Набор 1 «Тихая гавань» — 540 руб/шт",
    "Набор 2 «Золотой час» — 610 руб/шт",
    "Набор 3 «Пир на весь мир» — 490 руб/шт",
    "Набор 4 «Терракот» — 520 руб/шт",
    "Набор 5 «Красный бархат» — 670 руб/шт",
    "Набор 6 «Строгая классика» — 520 руб/шт",
    "Набор 7 «Ты и я» — 470 руб/шт",
    "Набор 8 «Привет из детства» — 640 руб/шт",
    "Набор 9 «Сочная классика» — 750 руб/шт",
    "Набор 10 «Нежная олива» — 570 руб/шт",
    "Набор 11 «Любовь спасёт мир» — 480 руб/шт",
    "Набор 12 «Ничего лишнего» — 280 руб/шт",
]

# Состояние карусели: user_id -> текущая страница
carousel_page = {}
# Выбранный набор: user_id -> номер страницы
selected_set = {}
# Режим калькулятора
calc_mode = {}



SYSTEM_PROMPT = """Твоё имя — Дима. Ты — ИИ-помощник компании «Красная Печать» из Омска. Вы занимаетесь свадебной полиграфией.

Твоя задача — провести клиента по воронке продаж:

ШАГ 1. Поздоровайся, представься что тебя зовут Дима и ты ИИ-помощник компании «Красная Печать», и спроси что нужно клиенту:
- Пригласительные (наборы)
- Карточки рассадки
- Холсты из фотографий
- Бонбоньерки

Если в начале диалога указан конкретный набор (например "[Клиент выбрал: Набор 2 «Золотой час»]") — сразу упомяни его и спроси детали по нему.

ШАГ 2. Уточни детали: количество, дата свадьбы, стиль, нужен ли индивидуальный дизайн.
Если клиент скидывает фото или говорит о конкретном дизайне — скажи что уточняешь стоимость у менеджера и напиши в конце:
СПРОСИ_ХОЗЯИНА: <что именно хочет клиент и сколько штук>

ШАГ 3. Когда хозяин сообщит цену через "ЦЕНА: 5000" — используй её и озвучь клиенту итог.

ШАГ 4. Когда клиент согласен — напиши в конце:
ИТОГ: <сумма цифрами>
СОСТАВ: <краткое описание>

Наборы пригласительных с ценами за штуку (от 4 шт):
- Набор 1 «Тихая гавань» — 540 руб/шт
- Набор 2 «Золотой час» — 610 руб/шт
- Набор 3 «Пир на весь мир» — 490 руб/шт
- Набор 4 «Терракот» — 520 руб/шт
- Набор 5 «Красный бархат» — 670 руб/шт
- Набор 6 «Строгая классика» — 520 руб/шт
- Набор 7 «Ты и я» — 470 руб/шт
- Набор 8 «Привет из детства» — 640 руб/шт
- Набор 9 «Сочная классика» — 750 руб/шт
- Набор 10 «Нежная олива» — 570 руб/шт
- Набор 11 «Любовь спасёт мир» — 480 руб/шт
- Набор 12 «Ничего лишнего» — 280 руб/шт

Базовые цены на остальное:
- Карточки рассадки: от 40 руб/шт
- Холст 30х40: от 1200 руб, 40х60: от 1800 руб, Диптих: от 2200 руб
- Бонбоньерки крафт: от 60 руб/шт, мешочек: от 80 руб/шт, тубус: от 95 руб/шт
Минимальная сумма: 2000 руб. Срок: 5-10 рабочих дней.

Правила:
- Говори дружелюбно и тепло
- Задавай по 1-2 вопроса за раз
- Никогда не показывай прайс списком"""

user_histories = {}
reminders = {}

MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📖 Каталог наборов", callback_data="pricelist")],
    [InlineKeyboardButton("💬 Подобрать набор", callback_data="chat")],
    [InlineKeyboardButton("🧮 Калькулятор", callback_data="calc")],
    [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
    [InlineKeyboardButton("🎓 Курс полиграфии на дому", callback_data="course")],
    [InlineKeyboardButton("📍 О нас", callback_data="about")],
    [InlineKeyboardButton("📞 Связаться с менеджером", url="https://t.me/redstamp55")],
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

    elif data == "pricelist":
        user_id = query.from_user.id
        carousel_page[user_id] = 0
        page = 0
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️", callback_data="carousel_prev"),
                InlineKeyboardButton(f"{page+1} / {len(PRICE_PAGES)}", callback_data="carousel_noop"),
                InlineKeyboardButton("▶️", callback_data="carousel_next"),
            ],
            [InlineKeyboardButton("💬 Хочу этот набор!", callback_data="want_set")],
            [InlineKeyboardButton("← В меню", callback_data="main")]
        ])
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=PRICE_PAGES[page],
            reply_markup=keyboard
        )

    elif data in ("carousel_prev", "carousel_next", "carousel_noop"):
        user_id = query.from_user.id
        page = carousel_page.get(user_id, 0)
        if data == "carousel_next":
            page = (page + 1) % len(PRICE_PAGES)
        elif data == "carousel_prev":
            page = (page - 1) % len(PRICE_PAGES)
        carousel_page[user_id] = page
        is_last = page == len(PRICE_PAGES) - 1
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️", callback_data="carousel_prev"),
                InlineKeyboardButton(f"{page+1} / {len(PRICE_PAGES)}", callback_data="carousel_noop"),
                InlineKeyboardButton("▶️", callback_data="carousel_next"),
            ],
            [InlineKeyboardButton("💬 Хочу этот набор!", callback_data="want_set")],
            [InlineKeyboardButton("← В меню", callback_data="main")]
        ])
        try:
            await context.bot.edit_message_media(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                media=__import__('telegram').InputMediaPhoto(media=PRICE_PAGES[page]),
                reply_markup=keyboard
            )
            if is_last:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Посмотрели все наборы? 😊\n\nЕсли понравился какой-то — нажмите кнопку ниже и Дима поможет рассчитать стоимость!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💬 Подобрать набор", callback_data="chat")]
                    ])
                )
        except Exception as e:
            logging.error(f"Carousel error: {e}")

    elif data == "want_set":
        user_id = query.from_user.id
        page = carousel_page.get(user_id, 0)
        selected_set[user_id] = page
        set_name = PRICE_NAMES[page]
        user_histories[user_id] = [
            {"role": "user", "content": f"[Клиент выбрал: {set_name}]"}
        ]
        await query.answer()
        # Отправляем фото набора + начинаем диалог
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=PRICE_PAGES[page],
            caption=f"Отличный выбор! {set_name.split('—')[0].strip()} 💍\n\nДима уже готов помочь с деталями 👇"
        )
        # Генерируем первое сообщение Димы
        response = await ai_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=500,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
        )
        reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply})
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=reply,
            reply_markup=BACK
        )

    elif data == "calc":
        user_id = query.from_user.id
        calc_mode[user_id] = True
        await query.edit_message_text(
            "🧮 Калькулятор\n\n"
            "Введите количество гостей — и я подберу подходящие наборы и посчитаю примерную стоимость!\n\n"
            "Напишите число 👇",
            reply_markup=BACK
        )

    elif data == "about":
        await query.edit_message_text(
            "📍 О нас\n\n"
            "Красная Печать — студия свадебной полиграфии из Омска.\n\n"
            "Мы создаём пригласительные, карточки рассадки, холсты и бонбоньерки — всё что делает вашу свадьбу особенной.\n\n"
            "Работаем по всей России. Доставка через СДЭК и Почту России, самовывоз в Омске.\n\n"
            "Минимальный заказ от 1 штуки. Срок изготовления 5-10 рабочих дней.",
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

    # Калькулятор
    if calc_mode.get(user_id):
        calc_mode.pop(user_id, None)
        try:
            guests = int("".join(filter(str.isdigit, text)))
            if guests < 4:
                await update.message.reply_text(
                    "Минимальный заказ — от 4 штук.\nВведите количество гостей от 4:",
                    reply_markup=BACK
                )
                calc_mode[user_id] = True
                return

            budget = sorted(PRICE_NAMES, key=lambda x: int(x.split("—")[1].replace("руб/шт", "").strip()))
            cheap = budget[0]
            mid = budget[len(budget)//2]
            prem = budget[-1]

            def price(name, qty):
                p = int(name.split("—")[1].replace("руб/шт", "").strip())
                return p * qty

            await update.message.reply_text(
                f"🧮 Расчёт для {guests} гостей:\n\n"
                f"💚 Бюджетный вариант\n{cheap.split('—')[0].strip()}\n"
                f"Стоимость: {price(cheap, guests):,} руб\n\n"
                f"💛 Средний вариант\n{mid.split('—')[0].strip()}\n"
                f"Стоимость: {price(mid, guests):,} руб\n\n"
                f"❤️ Премиум вариант\n{prem.split('—')[0].strip()}\n"
                f"Стоимость: {price(prem, guests):,} руб\n\n"
                f"Цены указаны за пригласительные. Карточки рассадки, бонбоньерки и доставка рассчитываются отдельно.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Подобрать набор с Димой", callback_data="chat")],
                    [InlineKeyboardButton("📖 Посмотреть каталог", callback_data="pricelist")],
                    [InlineKeyboardButton("← В меню", callback_data="main")],
                ])
            )
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("Введите просто число, например: 50", reply_markup=BACK)
            calc_mode[user_id] = True
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
