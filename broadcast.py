import os
import asyncio
import re
import json
import logging
import sys
import requests
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, BadRequest

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK")
RENDER_API_URL = "https://telegram-club-bot-z7xk.onrender.com/api/subscribers"
WAITLIST_FILE = "waitlist.txt"
SUBSCRIBERS_FILE = "subscribers.json"

# Logging functionality
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_subscriber_ids():
    """Load subscriber IDs from Render API (with local fallback)."""
    # Try fetching from Render API first
    try:
        logger.info("📡 Fetching subscribers from Render API...")
        response = requests.get(RENDER_API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            subscriber_ids = set(data.get('subscriber_ids', []))
            logger.info(f"✅ Got {len(subscriber_ids)} subscribers from Render API")
            return subscriber_ids
        else:
            logger.warning(f"Render API returned {response.status_code}")
    except Exception as e:
        logger.warning(f"Could not fetch from Render API: {e}")
    
    # Fallback to local file
    logger.info("📂 Falling back to local subscribers.json...")
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            data = json.load(f)
            return set(int(chat_id) for chat_id in data.keys())
    except Exception as e:
        logger.error(f"Error loading local subscribers: {e}")
        return set()


async def broadcast(message_text):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in .env")
        return

    if not os.path.exists(WAITLIST_FILE):
        logger.error(f"File {WAITLIST_FILE} not found. No one to broadcast to.")
        return

    bot = Bot(token=BOT_TOKEN)
    
    # 1. Load subscriber IDs to exclude
    subscriber_ids = load_subscriber_ids()
    if subscriber_ids:
        logger.info(f"📋 Found {len(subscriber_ids)} paying subscribers - they will be SKIPPED")
    
    # 2. Parse User IDs from waitlist
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
    
    # 3. Exclude subscribers from broadcast
    non_subscribers = user_ids - subscriber_ids
    skipped_count = len(user_ids) - len(non_subscribers)
    
    if skipped_count > 0:
        logger.info(f"⏭️ Skipping {skipped_count} users who already paid")

    logger.info(f"📢 Starting broadcast to {len(non_subscribers)} non-paying users...")
    logger.info(f"✉️ Message: {message_text[:50]}...")

    # 4. Send Messages
    success_count = 0
    fail_count = 0

    for user_id in non_subscribers:
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
