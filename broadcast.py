import os
import asyncio
import re
import logging
import sys
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, BadRequest

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK")
WAITLIST_FILE = "waitlist.txt"

# Logging functionality
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def broadcast(message_text):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in .env")
        return

    if not os.path.exists(WAITLIST_FILE):
        logger.error(f"File {WAITLIST_FILE} not found. No one to broadcast to.")
        return

    bot = Bot(token=BOT_TOKEN)
    
    # 1. Parse User IDs
    user_ids = set()
    try:
        with open(WAITLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                # Expecting line format: "Name (@user) - ID: 12345"
                match = re.search(r"ID:\s*(\d+)", line)
                if match:
                    user_ids.add(int(match.group(1)))
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return

    if not user_ids:
        logger.warning("No User IDs found in waitlist.txt.")
        return

    logger.info(f"📢 Starting broadcast to {len(user_ids)} users...")
    logger.info(f"✉️ Message: {message_text[:50]}...")

    # 2. Send Messages
    success_count = 0
    fail_count = 0

    for user_id in user_ids:
        try:
            # Create Keyboard with Payment Link (includes user ID for tracking)
            reply_markup = None
            if PAYMENT_LINK:
                # Append user ID to URL for webhook matching
                separator = "&" if "?" in PAYMENT_LINK else "?"
                tracked_url = f"{PAYMENT_LINK}{separator}tg_id={user_id}"
                keyboard = [
                    [InlineKeyboardButton("💎 Вступить в Клуб", url=tracked_url)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

            await bot.send_message(
                chat_id=user_id, 
                text=message_text, 
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            success_count += 1
            # Rate limit safety (Telegram allows ~30/sec, but let's be safe with 20/sec)
            await asyncio.sleep(0.05) 
        except Forbidden:
            logger.warning(f"❌ User {user_id} blocked the bot.")
            fail_count += 1
        except BadRequest as e:
            logger.warning(f"❌ Failed to pay {user_id}: {e}")
            fail_count += 1
        except Exception as e:
            logger.error(f"❌ Error for {user_id}: {e}")
            fail_count += 1

    logger.info(f"✅ Broadcast finished.")
    logger.info(f"Success: {success_count}")
    logger.info(f"Failed: {fail_count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 broadcast.py \"Your message here\"")
        sys.exit(1)
    
    message = sys.argv[1]
    asyncio.run(broadcast(message))
