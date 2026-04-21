import logging
import os
from anthropic import AsyncAnthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8621586893:AAEDvHWz2zPBYxi7qCD63ZI6_2txPBHe-6g")
KIE_API_KEY = os.environ.get("KIE_API_KEY", "78ab49cc731accab5c12f7aa89e261b5")
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "390540012:LIVE:94857")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "8143913122")

client = AsyncAnthropic(
    api_key=KIE_API_KEY,
    base_url="https://api.kie.ai"
)

SYSTEM_PROMPT = """Твоё имя — Дима. Ты — ИИ-помощник компании «Красная Печать» из Омска. Вы занимаетесь свадебной полиграфией.

Твоя задача — провести клиента по воронке продаж:

ШАГ 1. Поздоровайся, представься что тебя зовут Дима и ты ИИ-помощник компании «Красная Печать», и спроси что нужно клиенту. Узнай какие позиции его интересуют:
- Пригласительные
- Карточки рассадки
- Холсты из фотографий
- Бонбоньерки (подарки гостям)

ШАГ 2. Уточни детали:
- Количество штук
- Дата свадьбы
- Пожелания по стилю и цвету
- Если клиент скидывает фото или говорит о конкретном дизайне — скажи что уточняешь стоимость у менеджера и напиши в конце сообщения: СПРОСИ_ХОЗЯИНА: <описание что именно хочет клиент и сколько штук>

ШАГ 3. Когда хозяин сообщит тебе цену через сообщение вида "ЦЕНА: 5000" — используй эту цену для расчёта и озвучь клиенту итоговую сумму.

ШАГ 4. Когда клиент согласен с суммой — напиши в конце сообщения:
ИТОГ: <сумма цифрами, только число>
СОСТАВ: <краткое описание заказа>

Базовые цены (только для стандартных позиций без индивидуального дизайна):
- Карточки рассадки: от 40 руб/шт
- Холст 30х40 см: от 1200 руб, 40х60 см: от 1800 руб, Диптих: от 2200 руб
- Бонбоньерки крафт: от 60 руб/шт, атласный мешочек: от 80 руб/шт, тубус: от 95 руб/шт
Минимальная сумма заказа: 2000 руб. Срок: 5-10 рабочих дней.

Правила:
- Говори дружелюбно и тепло
- Задавай по 1-2 вопроса за раз
- Если клиент скидывает фото или просит индивидуальный дизайн — ВСЕГДА уточняй цену у хозяина
- Никогда не называй цену на пригласительные сам — только через хозяина"""

user_histories = {}
# pending_price[client_user_id] = True означает что ждём цену от хозяина
pending_price = {}

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
        "Привет! Меня зовут Дима — я ИИ-помощник компании «Красная Печать» 🤖\n\n"
        "Помогу подобрать свадебную полиграфию и рассчитаю стоимость. "
        "Если понадобится живой менеджер — сразу передам!"
    )
    await update.message.reply_text(
        "Вот что я умею — выбирайте:",
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
            "Вот что я умею — выбирайте:",
            reply_markup=MAIN_MENU
        )

    elif data == "chat":
        user_histories[user_id] = []
        await query.edit_message_text(
            "Отлично! Давайте подберём всё что нужно для вашей свадьбы.\n\n"
            "Напишите что вас интересует 👇",
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
            "Да, правки вносим до полного согласования.\n\n"
            "*Как происходит доставка?*\n"
            "Доставляем по всей России через СДЭК и Почту России. "
            "Самовывоз тоже доступен — мы находимся в Омске.\n\n"
            "*Можно ли заказать индивидуальный дизайн?*\n"
            "Конечно! Разработка индивидуального макета — 1 000 руб.\n\n"
            "*Как оплатить заказ?*\n"
            "После согласования заказа мы пришлём счёт прямо в этот чат.",
            parse_mode="Markdown",
            reply_markup=BACK
        )

    elif data == "course":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить 9 900 руб", callback_data="pay_course")],
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
            "✅ Отдельный урок по изготовлению пригласительных — аккуратно, красиво и эстетично\n"
            "✅ *Урок по продажам* — как зарабатывать, кому продавать, как формировать цену\n\n"
            "💡 *Бонус!* При оплате в течение 24 часов — личная консультация на 30 минут!",
            parse_mode="Markdown",
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
            need_name=True,
            need_phone_number=True,
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    chat_id = str(update.message.chat_id)

    # Сообщение от хозяина с ценой: "ЦЕНА: 5000 для клиента 123456"
    if chat_id == OWNER_CHAT_ID and text.startswith("ЦЕНА:"):
        parts = text.split()
        # Ожидаем формат: ЦЕНА: 5000 клиент: 123456789
        try:
            price = int("".join(filter(str.isdigit, parts[1])))
            # Найти client_id из сообщения
            client_id = None
            for i, p in enumerate(parts):
                if "клиент" in p.lower() and i + 1 < len(parts):
                    client_id = int(parts[i + 1])
            if client_id and client_id in user_histories:
                # Добавляем цену в историю как системное сообщение
                user_histories[client_id].append({
                    "role": "user",
                    "content": f"[СИСТЕМНОЕ СООБЩЕНИЕ ОТ ХОЗЯИНА]: Цена для этого клиента — {price} руб. Используй эту цену в расчёте и озвучь клиенту итоговую сумму."
                })
                # Генерируем ответ Димы клиенту
                reply = ""
                async with client.messages.stream(
                    model="claude-sonnet-4-5",
                    max_tokens=500,
                    system=SYSTEM_PROMPT,
                    messages=user_histories[client_id]
                ) as stream:
                    async for chunk in stream.text_stream:
                        reply += chunk
                user_histories[client_id].append({"role": "assistant", "content": reply})
                await context.bot.send_message(chat_id=client_id, text=reply)
                await update.message.reply_text(f"✅ Цена передана клиенту {client_id}")
            else:
                await update.message.reply_text("Не нашёл клиента. Формат: ЦЕНА: 5000 клиент: 123456789")
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("Ошибка. Формат: ЦЕНА: 5000 клиент: 123456789")
        return

    # Обычное сообщение от клиента
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})
    await update.message.chat.send_action("typing")

    try:
        reply = ""
        async with client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=user_histories[user_id]
        ) as stream:
            async for chunk in stream.text_stream:
                reply += chunk

        user_histories[user_id].append({"role": "assistant", "content": reply})

        # Дима хочет спросить хозяина о цене
        if "СПРОСИ_ХОЗЯИНА:" in reply:
            lines = reply.split("\n")
            clean_reply = ""
            question = ""
            for line in lines:
                if line.startswith("СПРОСИ_ХОЗЯИНА:"):
                    question = line.replace("СПРОСИ_ХОЗЯИНА:", "").strip()
                else:
                    clean_reply += line + "\n"
            await update.message.reply_text(clean_reply.strip())
            # Уведомляем хозяина
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"❗️ *Запрос цены от Димы*\n\n"
                     f"👤 Клиент: {update.effective_user.full_name} (id: {user_id})\n\n"
                     f"📋 Что хочет: {question}\n\n"
                     f"Ответь в формате:\n`ЦЕНА: 5000 клиент: {user_id}`",
                parse_mode="Markdown"
            )

        # Клиент согласился — отправляем счёт
        elif "ИТОГ:" in reply and "СОСТАВ:" in reply:
            lines = reply.split("\n")
            amount = None
            description = "Заказ свадебной полиграфии"
            clean_reply = ""
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
                await context.bot.send_invoice(
                    chat_id=update.message.chat_id,
                    title="Заказ — Красная Печать",
                    description=description,
                    payload=f"order_{user_id}",
                    provider_token=PAYMENT_TOKEN,
                    currency="RUB",
                    prices=[LabeledPrice("Оплата заказа 100%", amount * 100)],
                    need_name=True,
                    need_phone_number=True,
                )
        else:
            await update.message.reply_text(
                reply,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← В меню", callback_data="main")]
                ])
            )

    except Exception as e:
        logging.error(f"API error: {e}")
        await update.message.reply_text(
            "Что-то пошло не так. Попробуйте ещё раз или вернитесь в меню.",
            reply_markup=BACK
        )

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    amount = payment.total_amount // 100
    charge_id = payment.provider_payment_charge_id
    user_name = update.effective_user.full_name

    logging.info(f"Оплата! user_id={user_id}, сумма={amount} руб, charge_id={charge_id}")

    await update.message.reply_text(
        f"✅ Оплата {amount} руб получена!\n\n"
        f"Спасибо! Менеджер свяжется с вами в ближайшее время для уточнения деталей.",
        reply_markup=MAIN_MENU
    )

    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=f"💰 *Новая оплата!*\n\n"
             f"👤 Клиент: {user_name} (id: {user_id})\n"
             f"💵 Сумма: {amount} руб\n"
             f"🔖 ID транзакции: {charge_id}",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
