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



SYSTEM_PROMPT = """Твоё имя — Дима. Ты — ИИ-помощник компании «Красная Печать» из Омска. Свадебная полиграфия.

СТРОГИЙ СЦЕНАРИЙ:

Если в начале диалога указан выбранный набор и цена:
1. Клиент называет количество → считаешь сумму (количество × цена)
2. ПЕРЕД тем как выставить счёт — спроси ОДИН раз: "Нужны карточки рассадки или подарки гостям в том же стиле? Можем сделать всё в едином оформлении 😊"
3. Если клиент говорит "нет" или "не нужно" — СРАЗУ пиши:
ИТОГ: <сумма числом>
СОСТАВ: <название набора, количество штук>
4. Если клиент соглашается на доп. товары — уточни количество, добавь к сумме и пиши ИТОГ и СОСТАВ.

Больше ничего лишнего не спрашивай.

Если клиент скидывает ФОТО своей свадьбы, декора или цветов — посмотри на цвета и стиль, порекомендуй 2-3 подходящих набора из каталога с объяснением почему они подойдут.

Если клиент написал без выбранного набора — спроси только одно: что его интересует.

КАТАЛОГ ТОВАРОВ:

1. НАБОРЫ ПРИГЛАСИТЕЛЬНЫХ (цена за штуку, от 4 шт):
- Набор 1 «Тихая гавань» — 540 руб/шт (нежные бежево-серые тона, морской стиль)
- Набор 2 «Золотой час» — 610 руб/шт (зелёно-золотые тона, природные мотивы)
- Набор 3 «Пир на весь мир» — 490 руб/шт (алый и белый, старорусский стиль)
- Набор 4 «Терракот» — 520 руб/шт (терракотовые тона, природные оттенки)
- Набор 5 «Красный бархат» — 670 руб/шт (бордовый бархат, синий лайнер, роскошь)
- Набор 6 «Строгая классика» — 520 руб/шт (чёрно-белый минимализм)
- Набор 7 «Ты и я» — 470 руб/шт (современный, с полноцветной фотопечатью)
- Набор 8 «Привет из детства» — 640 руб/шт (бордовый, с детскими фото пары)
- Набор 9 «Сочная классика» — 750 руб/шт (зелёный с розовым, объёмная печать)
- Набор 10 «Нежная олива» — 570 руб/шт (оливковый, золотая сургучная печать)
- Набор 11 «Любовь спасёт мир» — 480 руб/шт (нюдово-бежевый, золотое фольгирование)
- Набор 12 «Ничего лишнего» — 280 руб/шт (минимализм, калька, сургуч)

2. КАРТОЧКИ РАССАДКИ (в стиле пригласительных): от 40 руб/шт
3. МЕНЮ: уточняй у менеджера (СПРОСИ_ХОЗЯИНА)
4. ХОЛСТЫ НА ПОДРАМНИКЕ (галерейная натяжка, срок до 3 дней):
Стандартные размеры:
0,2×0,3=1652р, 0,3×0,3=1596р, 0,3×0,4=2282р, 0,4×0,4=2380р, 0,4×0,5=2520р, 0,5×0,5=2842р, 0,4×0,6=3010р, 0,6×0,8=3563р, 0,8×1,1=6020р, 0,5×0,6=3360р

Особые варианты холстов:
- ЗВЁЗДНАЯ КАРТА — карта звёздного неба над вами в момент предложения руки и сердца, первого поцелуя, рождения ребёнка или любой важной даты. Указываете дату, время и город — мы делаем персональную карту с подписью. Цены как у холстов: 0,2×0,3=1652р, 0,3×0,3=1596р, 0,3×0,4=2282р, 0,4×0,4=2380р, 0,4×0,5=2520р, 0,5×0,5=2842р, 0,4×0,6=3010р, 0,6×0,8=3563р, 0,8×1,1=6020р, 0,5×0,6=3360р
5. НАКЛЕЙКИ С ИНИЦИАЛАМИ (золото/серебро): уточняй у менеджера (СПРОСИ_ХОЗЯИНА)
6. ПОДАРКИ ГОСТЯМ (всё брендированное):
🍯 Вкусное: мёд с биркой, шоколадки, варенье, чай с фото пары
✨ Красивое: свечи с монограммой, саше, магниты с фото "Спасибо что были с нами"
🎯 Полезное: закладка с монограммой, мини-блокнот, брендированные ручки
Цены — уточняй у менеджера (СПРОСИ_ХОЗЯИНА)
7. БОНБОНЬЕРКИ: крафт от 60р, мешочек от 80р, тубус от 95р

Минимальная сумма: 2000 руб.

Правила:
- Говори коротко и дружелюбно
- Предлагай докупить ОДИН раз — не навязывай
- Никогда не показывай прайс списком
- Как только финальная сумма известна — СРАЗУ пиши ИТОГ и СОСТАВ"""

user_histories = {}
reminders = {}

MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📖 Наш каталог", callback_data="catalog")],
    [InlineKeyboardButton("❤️ Мне понравилось", callback_data="liked")],
    [InlineKeyboardButton("🧮 Калькулятор", callback_data="calc")],
    [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
    [InlineKeyboardButton("📍 О нас", callback_data="about")],
    [InlineKeyboardButton("📞 Связаться с менеджером", url="https://t.me/redstamp55")],
    [InlineKeyboardButton("🎓 Курс полиграфии на дому", callback_data="course")],
])

# Лайки: user_id -> set(номеров страниц)
user_likes = {}

CATALOG_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("✉️ Пригласительные", callback_data="pricelist")],
    [InlineKeyboardButton("🖼 Холсты и звёздные карты", callback_data="canvases")],
    [InlineKeyboardButton("🎁 Подарки гостям", callback_data="gifts")],
    [InlineKeyboardButton("← Назад", callback_data="main")],
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
        try:
            await query.edit_message_text("Вот что я умею — выбирайте:", reply_markup=MAIN_MENU)
        except:
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Вот что я умею — выбирайте:",
                reply_markup=MAIN_MENU
            )

    elif data == "catalog":
        await query.edit_message_text(
            "📖 Наш каталог\n\nВыберите категорию:",
            reply_markup=CATALOG_MENU
        )

    elif data == "canvases":
        await query.edit_message_text(
            "🖼 Холсты и звёздные карты\n\n"
            "Выберите размер — покажем пример и цену.\n\n"
            "Вы можете загрузить любую свою фотографию — мы напечатаем холст именно с ней! 📸",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("20×30 см", callback_data="canvas_20x30"),
                 InlineKeyboardButton("30×30 см", callback_data="canvas_30x30")],
                [InlineKeyboardButton("30×40 см", callback_data="canvas_30x40"),
                 InlineKeyboardButton("40×40 см", callback_data="canvas_40x40")],
                [InlineKeyboardButton("40×50 см", callback_data="canvas_40x50"),
                 InlineKeyboardButton("50×50 см", callback_data="canvas_50x50")],
                [InlineKeyboardButton("40×60 см", callback_data="canvas_40x60"),
                 InlineKeyboardButton("50×60 см", callback_data="canvas_50x60")],
                [InlineKeyboardButton("60×80 см", callback_data="canvas_60x80"),
                 InlineKeyboardButton("80×110 см", callback_data="canvas_80x110")],
                [InlineKeyboardButton("🌟 Звёздная карта", callback_data="starmap")],
                [InlineKeyboardButton("← Каталог", callback_data="catalog")],
            ])
        )

    elif data.startswith("canvas_"):
        sizes = {
            "canvas_20x30": ("20×30 см", 1652),
            "canvas_30x30": ("30×30 см", 1596),
            "canvas_30x40": ("30×40 см", 2282),
            "canvas_40x40": ("40×40 см", 2380),
            "canvas_40x50": ("40×50 см", 2520),
            "canvas_50x50": ("50×50 см", 2842),
            "canvas_40x60": ("40×60 см", 3010),
            "canvas_50x60": ("50×60 см", 3360),
            "canvas_60x80": ("60×80 см", 3563),
            "canvas_80x110": ("80×110 см", 6020),
        }
    elif data == "starmap":
        await query.edit_message_text(
            "🌟 Звёздная карта\n\n"
            "Карта звёздного неба над вами в момент предложения руки и сердца, "
            "первого поцелуя, рождения ребёнка или любой важной даты.\n\n"
            "Вы указываете дату, время и город — мы создаём персональную карту с вашей подписью.\n\n"
            "Выберите размер:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("20×30 см", callback_data="starmap_20x30"),
                 InlineKeyboardButton("30×30 см", callback_data="starmap_30x30")],
                [InlineKeyboardButton("30×40 см", callback_data="starmap_30x40"),
                 InlineKeyboardButton("40×40 см", callback_data="starmap_40x40")],
                [InlineKeyboardButton("40×50 см", callback_data="starmap_40x50"),
                 InlineKeyboardButton("50×50 см", callback_data="starmap_50x50")],
                [InlineKeyboardButton("40×60 см", callback_data="starmap_40x60"),
                 InlineKeyboardButton("50×60 см", callback_data="starmap_50x60")],
                [InlineKeyboardButton("60×80 см", callback_data="starmap_60x80"),
                 InlineKeyboardButton("80×110 см", callback_data="starmap_80x110")],
                [InlineKeyboardButton("← Назад", callback_data="canvases")],
            ])
        )

    elif data.startswith("starmap_"):
        sizes = {
            "starmap_20x30": ("20×30 см", 1652),
            "starmap_30x30": ("30×30 см", 1596),
            "starmap_30x40": ("30×40 см", 2282),
            "starmap_40x40": ("40×40 см", 2380),
            "starmap_40x50": ("40×50 см", 2520),
            "starmap_50x50": ("50×50 см", 2842),
            "starmap_40x60": ("40×60 см", 3010),
            "starmap_50x60": ("50×60 см", 3360),
            "starmap_60x80": ("60×80 см", 3563),
            "starmap_80x110": ("80×110 см", 6020),
        }
        size_name, price = sizes[data]
        await query.edit_message_text(
            f"🌟 Звёздная карта {size_name}\n\n"
            f"💰 Цена: {price:,} руб\n\n"
            f"Укажите дату, время и город — и мы создадим карту звёздного неба именно для вашего момента ✨\n\n"
            f"Срок изготовления: до 3 дней.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Заказать", url="https://t.me/redstamp55")],
                [InlineKeyboardButton("← Назад", callback_data="starmap")],
            ])
        )

    elif data == "gifts":
        await query.edit_message_text(
            "🎁 Подарки гостям\n\nВсё брендированное — делаем открытки и наклейки к любому подарку.\n\nВыберите категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍯 Вкусное", callback_data="gifts_food")],
                [InlineKeyboardButton("✨ Красивое", callback_data="gifts_beauty")],
                [InlineKeyboardButton("🎯 Полезное", callback_data="gifts_useful")],
                [InlineKeyboardButton("← Каталог", callback_data="catalog")],
            ])
        )

    elif data == "gifts_food":
        await query.edit_message_text(
            "🍯 Вкусное\n\n"
            "Всё с персональной биркой, обёрткой или этикеткой с именами пары.\n\n"
            "• Мёд в маленьких баночках с именной биркой\n"
            "• Шоколадки с персональной обёрткой\n"
            "• Варенье в мини-банках с именной биркой\n"
            "• Пакетик натурального чёрного чая с фотографией пары\n\n"
            "Стоимость рассчитывается индивидуально под тираж.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Узнать стоимость", url="https://t.me/redstamp55")],
                [InlineKeyboardButton("← Назад", callback_data="gifts")],
            ])
        )

    elif data == "gifts_beauty":
        await query.edit_message_text(
            "✨ Красивое\n\n"
            "Всё с монограммой или фото молодожёнов.\n\n"
            "• Свечи с монограммой — на выбор разные ароматы\n"
            "• Саше с ароматом — на выбор разные ароматы\n"
            "• Магниты с фото молодожёнов\n"
            "  «Спасибо что были с нами в этот день»\n\n"
            "Стоимость рассчитывается индивидуально под тираж.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Узнать стоимость", url="https://t.me/redstamp55")],
                [InlineKeyboardButton("← Назад", callback_data="gifts")],
            ])
        )

    elif data == "gifts_useful":
        await query.edit_message_text(
            "🎯 Полезное\n\n"
            "Всё с монограммой и датой свадьбы.\n\n"
            "• Закладка для книги с монограммой и датой свадьбы\n"
            "• Мини-блокнот с тиснением монограммы\n"
            "• Брендированные ручки\n\n"
            "Стоимость рассчитывается индивидуально под тираж.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Узнать стоимость", url="https://t.me/redstamp55")],
                [InlineKeyboardButton("← Назад", callback_data="gifts")],
            ])
        )

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
        liked = page in user_likes.get(user_id, set())
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️", callback_data="carousel_prev"),
                InlineKeyboardButton(f"{page+1} / {len(PRICE_PAGES)}", callback_data="carousel_noop"),
                InlineKeyboardButton("▶️", callback_data="carousel_next"),
            ],
            [
                InlineKeyboardButton("💔 Убрать" if liked else "❤️ Нравится", callback_data="toggle_like"),
                InlineKeyboardButton("💬 Хочу этот набор!", callback_data="want_set"),
            ],
            [InlineKeyboardButton("← В меню", callback_data="main")]
        ])
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=PRICE_PAGES[page],
            reply_markup=keyboard
        )
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=PRICE_PAGES[page],
            reply_markup=keyboard
        )

    elif data in ("carousel_prev", "carousel_next", "carousel_noop", "toggle_like"):
        user_id = query.from_user.id
        page = carousel_page.get(user_id, 0)

        if data == "toggle_like":
            likes = user_likes.setdefault(user_id, set())
            if page in likes:
                likes.discard(page)
                await query.answer("Убрано из понравившихся")
            else:
                likes.add(page)
                await query.answer(f"❤️ {PRICE_NAMES[page].split('—')[0].strip()} сохранён!")
        elif data == "carousel_next":
            page = (page + 1) % len(PRICE_PAGES)
        elif data == "carousel_prev":
            page = (page - 1) % len(PRICE_PAGES)

        carousel_page[user_id] = page
        is_last = page == len(PRICE_PAGES) - 1
        liked = page in user_likes.get(user_id, set())
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️", callback_data="carousel_prev"),
                InlineKeyboardButton(f"{page+1} / {len(PRICE_PAGES)}", callback_data="carousel_noop"),
                InlineKeyboardButton("▶️", callback_data="carousel_next"),
            ],
            [
                InlineKeyboardButton("💔 Убрать" if liked else "❤️ Нравится", callback_data="toggle_like"),
                InlineKeyboardButton("💬 Хочу этот набор!", callback_data="want_set"),
            ],
            [InlineKeyboardButton("← В меню", callback_data="main")]
        ])
        try:
            await context.bot.edit_message_media(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                media=__import__('telegram').InputMediaPhoto(media=PRICE_PAGES[page]),
                reply_markup=keyboard
            )
            if is_last and data != "toggle_like":
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Посмотрели все наборы? 😊\n\nЕсли понравился какой-то — нажмите ❤️ чтобы сохранить, или сразу «Хочу этот набор!»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❤️ Мне понравилось", callback_data="liked")]
                    ])
                )
        except Exception as e:
            logging.error(f"Carousel error: {e}")

    elif data == "liked":
        user_id = query.from_user.id
        likes = user_likes.get(user_id, set())
        if not likes:
            await query.answer("Вы ещё ничего не отметили ❤️", show_alert=True)
            return
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❤️ Ваши понравившиеся наборы ({len(likes)} шт):"
        )
        for page in sorted(likes):
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=PRICE_PAGES[page],
                caption=PRICE_NAMES[page],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Хочу этот набор!", callback_data="want_set")],
                ])
            )
            carousel_page[user_id] = page

    elif data == "want_set":
        user_id = query.from_user.id
        page = carousel_page.get(user_id, 0)
        selected_set[user_id] = page
        set_name = PRICE_NAMES[page]
        set_price = int(set_name.split("—")[1].replace("руб/шт", "").strip())

        user_histories[user_id] = [
            {
                "role": "user",
                "content": f"[Клиент выбрал: {set_name}. Цена за штуку: {set_price} руб. Минимум от 4 шт.]"
            },
            {
                "role": "assistant",
                "content": f"Отличный выбор! {set_name.split('—')[0].strip()} — один из наших любимых наборов 💍\n\nСколько пригласительных вам нужно?"
            }
        ]

        await query.answer()
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=PRICE_PAGES[page],
            caption=f"Отличный выбор! {set_name.split('—')[0].strip()} 💍"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Сколько пригласительных вам нужно?",
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
            "Мы делаем:\n"
            "✉️ Пригласительные — 12 авторских наборов\n"
            "🪑 Карточки рассадки — в стиле ваших пригласительных\n"
            "📋 Меню для гостей\n"
            "🖼 Холсты на подрамнике — от 0,2×0,3 до 0,8×1,1 м\n"
            "🌟 Звёздная карта — небо над вами в момент предложения или важной даты\n"
            "✨ Наклейки с инициалами — золото или серебро\n"
            "🎁 Подарки гостям — вкусное, красивое, полезное\n"
            "🎀 Бонбоньерки\n\n"
            "Всё брендированное — делаем открытки и наклейки к любому подарку.\n\n"
            "Работаем по всей России. Доставка через СДЭК и Почту России, самовывоз в Омске.\n\n"
            "Срок: полиграфия 5-10 дней, холсты до 3 дней.",
            reply_markup=BACK
        )

    elif data == "faq":
        await query.edit_message_text(
            "❓ Частые вопросы\n\n"
            "Что вы делаете?\n"
            "Пригласительные, карточки рассадки, меню, холсты на подрамнике, наклейки с инициалами, бонбоньерки.\n\n"
            "Какой минимальный тираж?\n"
            "От 1 штуки. Минимальная сумма заказа — 2 000 руб.\n\n"
            "Сколько времени занимает изготовление?\n"
            "Полиграфия — 5-10 рабочих дней. Холсты — до 3 дней.\n\n"
            "Можно ли внести правки в дизайн?\n"
            "Да, присылаем макет на согласование перед печатью.\n\n"
            "Как происходит доставка?\n"
            "СДЭК и Почта России по всей России. Самовывоз в Омске.\n\n"
            "Как оплатить заказ?\n"
            "Бот выставит счёт прямо в чат после согласования.",
            reply_markup=BACK
        )

    elif data == "course":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Подробнее о курсе", url="https://polychrom55-collab.github.io/Obuchenie")],
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

    elif data.startswith("canvas_"):
        sizes = {
            "canvas_20x30": ("20×30 см", 1652),
            "canvas_30x30": ("30×30 см", 1596),
            "canvas_30x40": ("30×40 см", 2282),
            "canvas_40x40": ("40×40 см", 2380),
            "canvas_40x50": ("40×50 см", 2520),
            "canvas_50x50": ("50×50 см", 2842),
            "canvas_40x60": ("40×60 см", 3010),
            "canvas_50x60": ("50×60 см", 3360),
            "canvas_60x80": ("60×80 см", 3563),
            "canvas_80x110": ("80×110 см", 6020),
        }
        size_name, price = sizes.get(data, ("?", 0))
        await query.edit_message_text(
            f"🖼 Холст {size_name}\n\n"
            f"💰 Цена: {price:,} руб\n\n"
            f"📸 Загрузите любую свою фотографию — мы напечатаем холст именно с ней!\n\n"
            f"Галерейная натяжка на подрамник из крепких пород дерева.\n"
            f"Срок изготовления: до 3 дней.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Заказать этот размер", url="https://t.me/redstamp55")],
                [InlineKeyboardButton("← Назад", callback_data="canvases")],
            ])
        )

    elif data.startswith("starmap_"):
        sizes = {
            "starmap_20x30": ("20×30 см", 1652),
            "starmap_30x30": ("30×30 см", 1596),
            "starmap_30x40": ("30×40 см", 2282),
            "starmap_40x40": ("40×40 см", 2380),
            "starmap_40x50": ("40×50 см", 2520),
            "starmap_50x50": ("50×50 см", 2842),
            "starmap_40x60": ("40×60 см", 3010),
            "starmap_50x60": ("50×60 см", 3360),
            "starmap_60x80": ("60×80 см", 3563),
            "starmap_80x110": ("80×110 см", 6020),
        }
        size_name, price = sizes.get(data, ("?", 0))
        await query.edit_message_text(
            f"🌟 Звёздная карта {size_name}\n\n"
            f"💰 Цена: {price:,} руб\n\n"
            f"Укажите дату, время и город — и мы создадим карту звёздного неба именно для вашего момента ✨\n\n"
            f"Срок изготовления: до 3 дней.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Заказать", url="https://t.me/redstamp55")],
                [InlineKeyboardButton("← Назад", callback_data="starmap")],
            ])
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

            budget = sorted(range(len(PRICE_NAMES)), key=lambda i: int(PRICE_NAMES[i].split("—")[1].replace("руб/шт", "").strip()))
            cheap_i = budget[0]
            mid_i = budget[len(budget)//2]
            prem_i = budget[-1]

            def price(i, qty):
                p = int(PRICE_NAMES[i].split("—")[1].replace("руб/шт", "").strip())
                return p * qty

            await update.message.reply_text(f"🧮 Расчёт для {guests} гостей:")

            # Бюджетный
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=PRICE_PAGES[cheap_i],
                caption=f"💚 Бюджетный вариант\n{PRICE_NAMES[cheap_i].split('—')[0].strip()}\nСтоимость: {price(cheap_i, guests):,} руб"
            )
            # Средний
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=PRICE_PAGES[mid_i],
                caption=f"💛 Средний вариант\n{PRICE_NAMES[mid_i].split('—')[0].strip()}\nСтоимость: {price(mid_i, guests):,} руб"
            )
            # Премиум
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=PRICE_PAGES[prem_i],
                caption=f"❤️ Премиум вариант\n{PRICE_NAMES[prem_i].split('—')[0].strip()}\nСтоимость: {price(prem_i, guests):,} руб"
            )

            await update.message.reply_text(
                "Цены указаны за пригласительные. Карточки рассадки, бонбоньерки и доставка рассчитываются отдельно.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📖 Посмотреть весь каталог", callback_data="pricelist")],
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
            if clean_reply.strip():
                await update.message.reply_text(clean_reply.strip())
            if amount and amount >= 100:
                reminders.pop(user_id, None)
                await context.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=f"📋 Новый заказ!\n\nКлиент: {name} (@{username}, id: {user_id})\nСостав: {description}\nСумма: {amount} руб\n\nОтправляю счёт клиенту..."
                )
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f"Отлично! Перед оплатой подготовьте данные для макета:\n\n"
                         f"• Имена молодожёнов\n"
                         f"• Дату и время свадьбы\n"
                         f"• Место проведения\n"
                         f"• Дресс-код (если есть)\n"
                         f"• Любые пожелания по тексту\n\n"
                         f"После оплаты пришлите всё это напрямую нашему менеджеру @redstamp55 — он подготовит макет на согласование перед печатью 🎨\n\n"
                         f"Выставляю счёт 👇",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📞 @redstamp55", url="https://t.me/redstamp55")]
                    ])
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

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({
        "role": "user",
        "content": "Клиент прислал фото своей свадьбы или декора. Посмотри на стиль и цвета и порекомендуй 2-3 подходящих набора из каталога с объяснением почему они подойдут."
    })

    await update.message.chat.send_action("typing")
    try:
        response = await ai_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=600,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
        )
        reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(
            reply,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 Посмотреть каталог", callback_data="pricelist")],
                [InlineKeyboardButton("← В меню", callback_data="main")]
            ])
        )
    except Exception as e:
        logging.error(f"Photo handler error: {e}")
        await update.message.reply_text("Не могу обработать фото. Попробуйте ещё раз.", reply_markup=BACK)


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
        f"✅ Оплата {amount} руб получена!\n\n"
        f"Спасибо! Вот что будет дальше:\n\n"
        f"📋 Пришлите нам:\n"
        f"• Имена молодожёнов\n"
        f"• Дату и время свадьбы\n"
        f"• Место проведения\n"
        f"• Дресс-код (если есть)\n"
        f"• Любые пожелания по тексту\n\n"
        f"🎨 Мы подготовим макет и отправим вам на согласование перед печатью.\n\n"
        f"⏱ Срок изготовления — 5-10 рабочих дней после утверждения макета.\n\n"
        f"Напишите менеджеру — он примет все детали и ответит на вопросы!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📞 Написать менеджеру", url="https://t.me/redstamp55")]
        ])
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

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc:
        await update.message.reply_text(f"file_id: {doc.file_id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_reminders, interval=3600, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
