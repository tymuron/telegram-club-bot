import os
import logging
import threading
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters, CallbackQueryHandler, ApplicationBuilder
from apscheduler.schedulers.background import BackgroundScheduler

# Import our subscription manager
import subscription_manager as sm

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
PAYMENT_PROVIDER_TOKEN_INTL = os.getenv("PAYMENT_PROVIDER_TOKEN_INTL")
PAYMENT_PROVIDER_TOKEN_INTL = os.getenv("PAYMENT_PROVIDER_TOKEN_INTL")
PAYMENT_PROVIDER_TOKEN_INTL = os.getenv("PAYMENT_PROVIDER_TOKEN_INTL")
PAYMENT_LINK = os.getenv("PAYMENT_LINK") # Link to Payment Page (GetCourse)
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
    "👋 Здравствуйте, <b>{name}</b>!\n\n"
    "Добро пожаловать домой. Я создала этого бота, чтобы открыть вам дверь в клуб «ТОЧКА ОПОРЫ».\n\n"
    "Это пространство, где мы возвращаем себе чувство опоры. Не через сложные теории, а через простые изменения в вашем доме.\n\n"
    "Здесь вы узнаете, как сделать так, чтобы стены не забирали силы, а заряжали вас.\n\n"
    "Выберите действие в меню ниже 👇"
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
    "<b>Стоимость:</b> 1490 рублей в месяц (цена чашки кофе с десертом).\n\n"
    "Готовы зажечь свет в своем окне?"
)

TEXT_JOIN = (
    "<b>💳 Вступить в Клуб «Точка опоры»</b>\n\n"
    "Чтобы вступить в Клуб, оформите ежемесячную подписку.\n\n"
    "<b>Что вы получаете:</b>\n"
    "✔️ Доступ к закрытому каналу с уроками и практиками.\n"
    "✔️ Доступ к чату участников (теплое комьюнити).\n"
    "✔️ Прямые эфиры и разборы со мной.\n\n"
    "💳 <b>Стоимость участия:</b> 1490 рублей/месяц.\n"
    "<i>(Списание происходит автоматически раз в 30 дней. Управление подпиской и отмена — через письмо от GetCourse).</i>\n\n"
    "Выберите способ оплаты:"
)

TEXT_WAITLIST_CONFIRM = (
    "<b>✅ Вы в списке!</b>\n\n"
    "Спасибо за интерес! Мы свяжемся с вами, когда откроем двери."
)

TEXT_CABINET = (
    "<b>👤 Личный кабинет</b>\n\n"
    "Здесь информация о вашей подписке.\n\n"
    "👤 <b>Статус:</b> Активна ✅\n"
    "📅 <b>Следующее списание:</b> Автоматически через GetCourse\n"
    "💳 <b>Управление:</b> Через письмо от GetCourse (поиск по 'GetCourse')\n\n"
    "Если вы захотите приостановить участие, используйте ссылку в письмах об оплате. Но мы будем скучать!"
)

TEXT_HELP = (
    "<b>🆘 Нужна помощь?</b>\n\n"
    "Если у вас возникли вопросы или проблемы с оплатой, напишите нам в поддержку:\n\n"
    "👉 @tymuron"
)

TEXT_SUCCESS = (
    "<b>🎉 Ура! Оплата прошла успешно!</b>\n\n"
    "Я счастлива видеть вас в нашем кругу. Ваше путешествие к дому, полному сил, начинается прямо сейчас.\n\n"
    "Нажмите на кнопку ниже, чтобы попасть в закрытый канал.\n\n"
    "⚠️ <b>Важно:</b> Ссылка действует 24 часа и только для вас. Не пересылайте её другим."
)

# --- KEYBOARDS ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🕯 О Клубе (Что внутри?)", callback_data="about")],
        [InlineKeyboardButton("💳 Вступить в Клуб", callback_data="join")],
        [InlineKeyboardButton("👤 Личный кабинет", callback_data="cabinet")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_about_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Хочу в Клуб (Перейти к оплате)", callback_data="join")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_join_menu(user_id: int = None):
    keyboard = []
    
    if PAYMENT_LINK:
        # Append user's Telegram ID to URL for webhook matching
        separator = "&" if "?" in PAYMENT_LINK else "?"
        tracked_url = f"{PAYMENT_LINK}{separator}tg_id={user_id}" if user_id else PAYMENT_LINK
        keyboard.append([InlineKeyboardButton("💳 Оплатить и вступить", url=tracked_url)])
    else:
        keyboard.append([InlineKeyboardButton("🙋‍♀️ Хочу в клуб! (Лист ожидания)", callback_data="join_waitlist")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    return InlineKeyboardMarkup(keyboard)

def get_cabinet_menu():
    keyboard = [
        [InlineKeyboardButton("📧 Написать в поддержку", url="https://t.me/tymuron")],
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
    waitlist_path = "/var/data/waitlist.txt" if os.path.exists("/var/data") else "waitlist.txt"
    try:
        with open(waitlist_path, "a", encoding="utf-8") as f:
            f.write(f"{user.first_name} {user.last_name} ({username}) - ID: {user.id}\n")
    except Exception as e:
        logger.error(f"Failed to save to waitlist: {e}")

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
        TEXT_WELCOME.format(name=user.first_name),
        reply_markup=get_main_menu()
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
            reply_markup=get_join_menu(user_id=update.effective_user.id),
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

async def testpay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin Only) Sends a test invoice."""
    user_id = update.effective_user.id
    
    # Security check: Only allow the Admin
    if str(user_id) != str(ADMIN_ID):
        return

    await send_invoice(context, update.effective_chat.id)

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

# --- NEW: Subscribers Command (Admin) ---
async def subscribers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin Only) Shows active subscribers."""
    user_id = update.effective_user.id
    
    if str(user_id) != str(ADMIN_ID):
        return

    subs = sm.get_all_active_subscribers()
    
    if not subs:
        await update.message.reply_text("📭 Нет активных подписчиков.")
        return
    
    text = f"<b>👥 Активные подписчики: {len(subs)}</b>\n\n"
    for s in subs[:20]:  # Limit to 20 for readability
        expires = datetime.fromisoformat(s['expires_at']).strftime('%d.%m.%Y')
        name = s.get('name') or s.get('email') or f"ID: {s['chat_id']}"
        text += f"• {name} (до {expires})\n"
    
    if len(subs) > 20:
        text += f"\n... и ещё {len(subs) - 20} человек"
    
    await update.message.reply_html(text)

# --- Global Application Reference for Scheduler ---
bot_application = None

# --- Scheduler Jobs ---
async def check_reminders_job():
    """Daily job: Send reminders to Day 27 subscribers."""
    if not bot_application:
        return
        
    logger.info("⏰ Running reminder check...")
    users = sm.get_subscribers_needing_reminder()
    
    for user in users:
        try:
            await bot_application.bot.send_message(
                chat_id=user['chat_id'],
                text=sm.REMINDER_TEXT,
                parse_mode="HTML"
            )
            sm.mark_reminder_sent(user['chat_id'])
            logger.info(f"📨 Sent reminder to {user['chat_id']}")
        except Exception as e:
            logger.error(f"Failed to send reminder to {user['chat_id']}: {e}")

async def check_expiries_job():
    """Daily job: Kick expired subscribers from channel."""
    if not bot_application:
        return
        
    logger.info("⏰ Running expiry check...")
    users = sm.get_expired_subscribers()
    
    for user in users:
        try:
            # Send warning message first
            if PAYMENT_LINK:
                warning = sm.EXPIRY_WARNING_TEXT.format(payment_link=PAYMENT_LINK)
            else:
                warning = sm.EXPIRY_WARNING_TEXT.format(payment_link="свяжитесь с @tymuron")
            
            await bot_application.bot.send_message(
                chat_id=user['chat_id'],
                text=warning,
                parse_mode="HTML"
            )
            
            # Kick from channel
            if CHANNEL_ID:
                await bot_application.bot.ban_chat_member(
                    chat_id=CHANNEL_ID,
                    user_id=user['chat_id']
                )
                # Immediately unban so they can rejoin if they pay again
                await bot_application.bot.unban_chat_member(
                    chat_id=CHANNEL_ID,
                    user_id=user['chat_id']
                )
                logger.info(f"🚫 Kicked expired user {user['chat_id']} from channel")
            
            sm.mark_expired(user['chat_id'])
            
            # Notify admin
            if ADMIN_ID:
                await bot_application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🚫 Удалён из канала (истекла подписка): {user.get('name') or user['chat_id']}"
                )
                
        except Exception as e:
            logger.error(f"Failed to process expiry for {user['chat_id']}: {e}")

def main() -> None:
    """Run the bot."""
    global bot_application
    
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()
    bot_application = application  # Store reference for scheduler

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("leads", leads))
    application.add_handler(CommandHandler("subscribers", subscribers_cmd))  # NEW
    application.add_handler(CallbackQueryHandler(menu_callback))
    application.add_handler(CommandHandler("testpay", testpay))
    
    # Payment Handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    print("Bot is running with Menus...")
    
    # Start Web Server for Render (Health Check + Webhook)
    app = Flask(__name__)

    @app.route('/')
    def health_check():
        return "Bot is alive!", 200

    @app.route('/api/subscribers', methods=['GET'])
    def get_subscribers_api():
        """Return list of subscriber IDs for broadcast filtering."""
        try:
            subscribers = sm.get_all_subscribers()
            subscriber_ids = [int(chat_id) for chat_id in subscribers.keys()]
            return jsonify({
                "status": "ok",
                "count": len(subscriber_ids),
                "subscriber_ids": subscriber_ids
            }), 200
        except Exception as e:
            logger.error(f"Error getting subscribers: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/webhook/payment', methods=['POST'])
    def payment_webhook():
        """Receive payment notifications from GetCourse."""
        try:
            data = request.json or {}
            logger.info(f"📥 Received webhook: {data}")
            
            parsed = sm.parse_getcourse_webhook(data)
            
            if not parsed or not parsed.get('chat_id'):
                logger.warning("Webhook missing chat_id, cannot link to Telegram user")
                return jsonify({"status": "ok", "note": "no chat_id"}), 200
            
            # Check payment status
            status = str(parsed.get('status', '')).lower()
            if status in ['completed', 'paid', 'оплачен', 'завершен', 'success']:
                sm.add_subscriber(
                    chat_id=parsed['chat_id'],
                    email=parsed.get('email'),
                    name=parsed.get('name')
                )
                logger.info(f"✅ Payment recorded for {parsed['chat_id']}")
                
                # Schedule async tasks to run on the main event loop
                chat_id = parsed['chat_id']
                user_name = parsed.get('name') or parsed.get('email') or str(chat_id)
                
                # We'll use a simple approach: store tasks to run later
                # For now, log and return - the user will get access via the channel
                logger.info(f"🎫 User {chat_id} should receive invite link")
                
                # Try to send messages using threading
                import threading
                def send_messages():
                    import asyncio
                    async def do_send():
                        try:
                            if CHANNEL_ID and bot_application:
                                # Create invite link
                                invite = await bot_application.bot.create_chat_invite_link(
                                    chat_id=CHANNEL_ID,
                                    member_limit=1,
                                    name=f"User {chat_id}"
                                )
                                # Send success message with invite link
                                keyboard = [[InlineKeyboardButton("🚪 Войти в Клуб", url=invite.invite_link)]]
                                await bot_application.bot.send_message(
                                    chat_id=chat_id,
                                    text=TEXT_SUCCESS,
                                    parse_mode="HTML",
                                    reply_markup=InlineKeyboardMarkup(keyboard)
                                )
                                logger.info(f"✅ Invite link sent to {chat_id}")
                            
                            if ADMIN_ID and bot_application:
                                await bot_application.bot.send_message(
                                    chat_id=ADMIN_ID,
                                    text=f"💰 Новая оплата!\n{user_name}"
                                )
                                logger.info(f"✅ Admin notified about {chat_id}")
                        except Exception as e:
                            logger.error(f"Failed to send messages: {e}")
                    
                    asyncio.run(do_send())
                
                thread = threading.Thread(target=send_messages)
                thread.start()
            
            return jsonify({"status": "ok"}), 200
            
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

from broadcast import check_campaign_job

# ... (Logging config usually here, but keeping file structure)

# --- WEBHOOK SERVER (Remote) ---
# ... (Existing code)

def run():
    """Runs the bot."""
    # Check if we are on Render (PORT exists)
    port = os.environ.get("PORT")
    
    # Setup Scheduler for daily checks (using BackgroundScheduler)
    scheduler = BackgroundScheduler()
    
    # Wrapper to run async jobs from background scheduler
    def run_async_job(coro_func):
        def wrapper():
            asyncio.run(coro_func())
        return wrapper
    
    scheduler.add_job(run_async_job(check_reminders_job), 'cron', hour=10, minute=0)  # 10:00 AM daily
    scheduler.add_job(run_async_job(check_expiries_job), 'cron', hour=10, minute=30)  # 10:30 AM daily
    
    # --- CAMPAIGN AUTOPILOT ---
    # Check for scheduled broadcast messages every minute
    scheduler.add_job(run_async_job(check_campaign_job), 'interval', minutes=1)
    
    scheduler.start()
    logger.info("📅 Scheduler started (Reminders 10:00, Expiries 10:30, Campaign every 1min)")

    # Define Bot Polling Function
    def run_telegram_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("🤖 Starting Telegram Bot Polling...")
        
        # Initialize Application
        global application
        application = ApplicationBuilder().token(BOT_TOKEN).build()

        # --- HANDLERS ---
        application.add_handler(CommandHandler("start", start))
        application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
        application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
        application.add_handler(CallbackQueryHandler(menu_callback))
        # ----------------

        async def start_bot():
            """Async function to properly start the bot without signal handlers."""
            await application.initialize()
            await application.start()
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("✅ Bot polling started successfully!")
            # Keep running forever
            while True:
                await asyncio.sleep(3600)  # Sleep 1 hour, repeat

        try:
            loop.run_until_complete(start_bot())
        except Exception as e:
            logger.error(f"❌ FATAL ERROR in Bot Polling: {e}", exc_info=True)

    # Start Telegram Bot in a separate thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    if port:
        # ON RENDER: Run Flask in Main Thread (Blocking)
        logger.info(f"🚀 STARTING FLASK ON MAIN THREAD PORT: {port}")
        
        # Determine Webhook Path
        WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
        
        app = Flask(__name__)
        
        @app.route(WEBHOOK_PATH, methods=['POST'])
        def webhook():
             """Handle incoming GetCourse payments."""
             try:
                # We need to manually parse the form-data from GetCourse
                # GetCourse sends: ID, status, uid, phone, email, name, etc.
                # We expect custom field 'tg_id' passed in link
                
                # Check query params for tg_id (we add it to payment link)
                chat_id = request.args.get('tg_id')
                
                # Fallback: check body
                if not chat_id and request.form.get('tg_id'):
                    chat_id = request.form.get('tg_id')
                
                if not chat_id:
                     # Just return OK for general status updates that don't concern us
                     return jsonify({"status": "ignored", "reason": "no tg_id"}), 200

                # Data from GetCourse
                status = request.form.get('status', '').lower() # paid, completed
                email = request.form.get('email')
                name = request.form.get('name')
                
                logger.info(f"💰 Payment Webhook: ID={chat_id} Status={status} Email={email}")
                
                if status in ['completed', 'paid', 'оплачен', 'завершен', 'success']:
                    # 1. Add to subscribers
                    sm.add_subscriber(
                        chat_id=int(chat_id),
                        email=email,
                        name=name
                    )

                    # 2. Send Telegram Invite (using global application)
                    async def send_invite():
                        try:
                            invite = await application.bot.create_chat_invite_link(
                                chat_id=CHANNEL_ID,
                                member_limit=1,
                                name=f"User {chat_id}"
                            )
                            keyboard = [[InlineKeyboardButton("🚪 Войти в Клуб", url=invite.invite_link)]]
                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=TEXT_SUCCESS,
                                parse_mode="HTML",
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                            # Notify Admin
                            if ADMIN_ID:
                                await application.bot.send_message(
                                    chat_id=ADMIN_ID,
                                    text=f"💰 New Payment!\n{name}\nID: {chat_id}"
                                )
                        except Exception as e:
                            logger.error(f"Failed to send invite: {e}")

                    # Run async send in background thread loop? 
                    # Actually, we can just fire-and-forget logic if strictly necessary, 
                    # but since we have a running loop in another thread, we should use run_coroutine_threadsafe if possible.
                    # SIMPLER: Create a temporary loop for this thread just to send.
                    # OR EVEN SIMPLER: The 'sm.add_subscriber' is persistent. The user will be added. 
                    # The message sending is a bonus.
                    
                    # Hack to run async in Flask thread:
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(send_invite())
                    loop.close()

                return jsonify({"status": "ok"}), 200

             except Exception as e:
                logger.error(f"Webhook error: {e}")
                return jsonify({"status": "error"}), 500
             
        # Just a health check endpoint
        @app.route("/", methods=['GET'])
        def health_check():
            return "Bot is running", 200

        # API: Get subscriber IDs for broadcast filtering
        @app.route('/api/subscribers', methods=['GET'])
        def get_subscribers_api():
            """Return list of subscriber IDs for broadcast filtering."""
            try:
                subs = sm.get_all_subscribers()
                subscriber_ids = [int(k) for k in subs.keys()]
                return jsonify({
                    "count": len(subscriber_ids),
                    "subscriber_ids": subscriber_ids
                }), 200
            except Exception as e:
                logger.error(f"API error: {e}")
                return jsonify({"error": str(e)}), 500

        # Run Flask (Blocks forever)
        app.run(host="0.0.0.0", port=int(port), debug=False, use_reloader=False)
    else:
        # LOCAL: Just wait forever (since bot is in thread)
        logger.warning("⚠️ No PORT found. Running locally. Press Ctrl+C to stop.")
        bot_thread.join()

if __name__ == "__main__":
    run()
