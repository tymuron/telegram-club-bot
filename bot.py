import os
import logging
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters, CallbackQueryHandler

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
PAYMENT_PROVIDER_TOKEN_INTL = os.getenv("PAYMENT_PROVIDER_TOKEN_INTL")
WAITLIST_LINK = os.getenv("WAITLIST_LINK")
WAITLIST_LINK = os.getenv("WAITLIST_LINK")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_ID")
CURRENCY = os.getenv("CURRENCY", "RUB")
PRICE_AMOUNT = 199000  # 1990.00 RUB
PRICE_LABEL = "Подписка 1 месяц"

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- TEXTS ---
TEXT_WELCOME = (
    "{name}, привет! Рада, что ты хочешь в клуб «Точка Опоры».\n\n"
    "🏠 <b>Добро пожаловать в пространство Анны Ромео</b>\n"
    "0% воды и сложной теории. Только практика для жизни.\n\n"
    "<b>Внутри:</b>\n\n"
    "🗝 <b>Закрытый Клуб «Точка Опоры»:</b> вход в пространство устойчивости.\n\n"
    "📅 <b>Темы месяца:</b> каждый месяц прорабатываем одну сферу (деньги, здоровье, отношения) через дом.\n\n"
    "🛋 <b>Инструменты Васту:</b> простые коррекции для квартир без ремонта и сноса стен.\n\n"
    "🫂 <b>Близкий круг:</b> чат с сильным окружением и поддержкой.\n\n"
    "👉 <b>Вы в списке ожидания!</b> Мы скоро свяжемся с вами."
)

TEXT_ABOUT = (
    "🏠 <b>Клуб «Точка опоры»</b> — это ваш остров устойчивости в мире, где всё слишком быстро меняется.\n\n"
    "Я создала его не для «учеников», а для людей, которым важно чувствовать себя дома безопасно и ресурсно. "
    "Моя цель — чтобы вы перестали бесконечно искать ответы и просто начали жить, чувствуя поддержку своего пространства.\n\n"
    "<b>Что для меня важно?</b>\n"
    "Я сторонник малых шагов. Не нужно сносить стены, чтобы стать счастливее. "
    "Иногда достаточно переставить кресло, добавить правильный свет или убрать лишнее, чтобы в жизни появился порядок вместо хаоса.\n\n"
    "Мы со-творцы своего дома. И дом имеет колоссальную силу влиять на наше состояние, деньги и отношения.\n\n"
    "✨ <b>Что мы будем делать?</b>\n"
    "В Клубе мы превращаем теорию Васту в простую практику.\n"
    "Каждый месяц — одна тема (Здоровье, Отношения, Финансы).\n"
    "Я даю вам короткие инструменты, вы внедряете их в квартире и наблюдаете, как меняется ваша реальность.\n\n"
    "Здесь мы рука об руку, без гонки и стресса, возвращаем себе право на уют и спокойствие.\n\n"
    "<b>Формат:</b> Закрытый Telegram-канал.\n"
    "<b>Стоимость:</b> 1990 рублей в месяц (цена чашки кофе с десертом).\n\n"
    "Готовы зажечь свет в своем окне?"
)

TEXT_JOIN = (
    "<b>🚀 Предзапись в Клуб «Точка опоры»</b>\n\n"
    "Мы пока не принимаем оплату автоматичеcки, но вы можете записаться в лист ожидания.\n\n"
    "<b>Что это дает?</b>\n"
    "Как только мы откроем двери, я лично свяжусь с вами и пришлю приглашение.\n\n"
    "Нажмите <b>«Хочу в клуб»</b>, чтобы я увидела ваш интерес. 👇"
)

TEXT_WAITLIST_CONFIRM = (
    "<b>✅ Вы в списке!</b>\n\n"
    "Но это еще не всё. Пока мы готовимся к запуску, я приглашаю вас в наш <b>Лист Ожидания</b> (отдельный канал).\n\n"
    "Там я буду публиковать новости и вышлю приглашение первыми.\n\n"
    "👇 <b>Нажмите, чтобы вступить:</b>"
)



TEXT_CABINET = (
    "Здесь информация о вашей подписке.\n\n"
    "👤 <b>Статус:</b> Не активна (Тестовый режим)\n"
    "📅 <b>Следующее списание:</b> -\n"
    "💳 <b>Карта:</b> -\n\n"
    "Если вы захотите приостановить участие, вы можете сделать это здесь. Но мы будем скучать!"
)

TEXT_HELP = (
    "Если у вас возникли вопросы или проблемы с оплатой, пожалуйста, напишите нам в поддержку: @tymuron"
)

# --- KEYBOARDS ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🕯 О Клубе (Что внутри?)", callback_data="about")],
        [InlineKeyboardButton("💳 Вступить в Клуб", callback_data="join")],
        [InlineKeyboardButton("👤 Личный кабинет / Подписка", callback_data="cabinet")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_about_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Хочу в Клуб (Предзапись)", callback_data="join")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_join_menu():
    keyboard = [
        [InlineKeyboardButton("🙋‍♀️ Хочу в клуб! (Лист ожидания)", callback_data="join_waitlist")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cabinet_menu():
    keyboard = [
        [InlineKeyboardButton("Изменить карту", callback_data="cabinet_dummy")],
        [InlineKeyboardButton("Отменить подписку", callback_data="cabinet_dummy")],
        [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main")]]
    return InlineKeyboardMarkup(keyboard)


# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends welcome message."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else "No Username"
    
    # Log the new user for the admin
    logger.info(f"🆕 NEW USER JOINED: {user.first_name} {user.last_name} ({username}, ID: {user.id})")
    print(f"!!! WELCOME: {user.first_name} ({username}) joined the waitlist! !!!")

    # Save to file
    with open("waitlist.txt", "a", encoding="utf-8") as f:
        f.write(f"{user.first_name} {user.last_name} ({username}) - ID: {user.id}\n")

    # Send Notification to Admin (Persistence)
    if ADMIN_ID:
        try:
            admin_text = (
                f"📝 <b>New Lead!</b>\n"
                f"Name: {user.first_name} {user.last_name}\n"
                f"Username: {username}\n"
                f"ID: <code>{user.id}</code>"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    await update.message.reply_html(
        TEXT_WELCOME.format(name=user.first_name)
        # No menu, just text as requested
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses Callback Queries."""
    query = update.callback_query
    await query.answer()

    data = query.data
    
    if data == "main":
        await query.edit_message_text(
            text=TEXT_WELCOME.format(name=update.effective_user.first_name),
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    elif data == "about":
        await query.edit_message_text(
            text=TEXT_ABOUT,
            reply_markup=get_about_menu(),
            parse_mode="HTML"
        )
    elif data == "join":
        await query.edit_message_text(
            text=TEXT_JOIN,
            reply_markup=get_join_menu(),
            parse_mode="HTML"
        )
    elif data == "join_waitlist":
        # Log interest and confirm
        user = query.from_user
        username = f"@{user.username}" if user.username else "No Username"
        logger.info(f"🆕 NEW LEAD from Bot: {user.first_name} {user.last_name} ({username}, ID: {user.id})")
        
        # In a real scenario, we might write to a file or DB here
        # For now, just logging to console/stdout is enough for the Admin to see in terminal
        print(f"!!! INTEREST: {user.first_name} ({username}) wants to join! !!!")

        # Check if we have a waitlist link
        keyboard = []
        if WAITLIST_LINK:
            keyboard.append([InlineKeyboardButton("🚪 Вступить в Лист Ожидания", url=WAITLIST_LINK)])
        keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="main")])

        await query.edit_message_text(
            text=TEXT_WAITLIST_CONFIRM if WAITLIST_LINK else "<b>✅ Вы в списке!</b>\n\nМы свяжемся с вами.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    elif data == "cabinet":
        await query.edit_message_text(
            text=TEXT_CABINET,
            reply_markup=get_cabinet_menu(),
            parse_mode="HTML"
        )
    elif data == "help":
        await query.edit_message_text(
            text=TEXT_HELP,
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
    elif data == "cabinet_dummy":
        await query.answer("Функция доступна только при активной подписке.", show_alert=True)

async def send_invoice(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    title = "Клуб «Точка опоры»"
    description = "Ежемесячная подписка на закрытый клуб."
    payload = "Club-Subscription"
    currency = CURRENCY
    price = int(PRICE_AMOUNT) 
    
    # We use the token from ENV, but strip it to be 100% safe
    token = PAYMENT_PROVIDER_TOKEN.strip()

    prices = [LabeledPrice("Подписка на 1 месяц", price)]

    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=token,
            currency=currency,
            prices=prices,
            start_parameter="club-sub",
        )
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        await context.bot.send_message(chat_id, f"⚠️ Ошибка при создании счета: {e}")

async def leads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin Only) Sends the waitlist file."""
    user_id = update.effective_user.id
    
    # Security check: Only allow the Admin to see this
    if str(user_id) != str(ADMIN_ID):
        return  # Ignore strangers

    if not os.path.exists("waitlist.txt"):
        await update.message.reply_text("📭 Список пока пуст.")
        return

    await update.message.reply_document(
        document=open("waitlist.txt", "rb"),
        caption="📂 Вот ваш список ожидания."
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query.invoice_payload != "Club-Subscription":
        await query.answer(ok=False, error_message="Ошибка оплаты.")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirms successful payment and sends invite link."""
    # Logic for successful payment
    
    # 1. Send Success Message with Invite Button
    try:
        # Create Invite Link
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"Sub: {update.effective_user.first_name}"
        )
        
        keyboard = [[InlineKeyboardButton("🚪 Войти в «Точка опоры»", url=invite_link.invite_link)]]
        
        await update.message.reply_html(
            TEXT_SUCCESS,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"Generated invite link for user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Failed to generate invite link: {e}")
        await update.message.reply_text(
            "⚠️ Ошибка генерации ссылки. Пожалуйста, напишите в поддержку, приложив скриншот оплаты."
        )

def main() -> None:
    """Run the bot."""
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("leads", leads))  # New Admin Command
    application.add_handler(CallbackQueryHandler(menu_callback))
    # DISABLE PAYMENTS FOR NOW
    # application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    # application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    print("Bot is running with Menus...")
    
    # Start Dummy Web Server for Render
    app = Flask(__name__)

    @app.route('/')
    def health_check():
        return "Bot is alive!", 200

    def run_flask():
        # Render provides PORT in env, default to 10000
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    # Run Flask in a separate thread so it doesn't block the bot
    threading.Thread(target=run_flask, daemon=True).start()

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
