
import os
import asyncio
import re
import json
import logging
import sys
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, BadRequest

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_LINK = os.getenv("PAYMENT_LINK")
RENDER_API_URL = "https://telegram-club-bot-z7xk.onrender.com/api/subscribers"

# Check persistent storage first (Render)
if os.path.exists("/var/data"):
    DATA_DIR = "/var/data"
else:
    DATA_DIR = "."

WAITLIST_FILE = os.path.join(DATA_DIR, "waitlist.txt")
# If waitlist is not on disk (first run), try loading from root
if not os.path.exists(WAITLIST_FILE) and os.path.exists("waitlist.txt"):
    WAITLIST_FILE = "waitlist.txt"

SUBSCRIBERS_FILE = "subscribers.json" # Local backup on Mac (keep as is for local running)
CAMPAIGN_CONFIG_FILE = "campaign_config.json"
CAMPAIGN_STATE_FILE = os.path.join(DATA_DIR, "campaign_state.json")

# Logging functionality
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_subscriber_ids():
    """Load subscriber IDs (paying users) to exclude them."""
    local_ids = set()
    remote_ids = set()
    
    # Load local subscribers first
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                data = json.load(f)
                local_ids = set(int(chat_id) for chat_id in data.keys())
        except Exception as e:
            logger.warning(f"Could not load local file: {e}")
    
    # Try fetching from Render API
    try:
        response = requests.get(RENDER_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            remote_ids = set(data.get('subscriber_ids', []))
    except:
        pass
    
    return local_ids | remote_ids

def load_target_users():
    """Load users from users.json (active funnel) who have NOT paid."""
    subscriber_ids = load_subscriber_ids()
    target_users = set()
    
    # 1. Try loading from users.json (The Database)
    users_file = os.path.join(DATA_DIR, "users.json")
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                users_db = json.load(f)
                for uid, user_data in users_db.items():
                    user_id = int(uid)
                    # Filter out those who paid or are blocked
                    if user_id not in subscriber_ids and user_data.get("status") != "blocked":
                        target_users.add(user_id)
            logger.info(f"Loaded {len(target_users)} active users from DB.")
            return target_users
        except Exception as e:
            logger.error(f"Error reading users.json: {e}")

    # 2. Fallback to waitlist.txt (Legacy)
    if not os.path.exists(WAITLIST_FILE):
        return set()

    try:
        with open(WAITLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                # Expecting line format: "Name (@user) - ID: 12345"
                match = re.search(r"ID:\s*(\d+)", line)
                if match:
                    user_id = int(match.group(1))
                    if user_id not in subscriber_ids:
                        target_users.add(user_id)
    except Exception as e:
        logger.error(f"Error reading waitlist: {e}")
        
    return target_users

def load_campaign_state():
    if os.path.exists(CAMPAIGN_STATE_FILE):
        try:
            with open(CAMPAIGN_STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {"sent_messages": []}
    return {"sent_messages": []}

def save_campaign_state(state):
    try:
        with open(CAMPAIGN_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

async def broadcast_message(message_config):
    """Send a specific message to all target users."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN missing")
        return

    bot = Bot(token=BOT_TOKEN)
    target_users = load_target_users()
    
    if not target_users:
        logger.info("No target users for broadcast.")
        return

    # Load Text
    text_content = ""
    if "text_file" in message_config:
        try:
            with open(message_config["text_file"], "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            logger.error(f"Could not read message file: {e}")
            return

    # Prepare Buttons
    reply_markup = None
    if message_config.get("buttons"):
        btn_text = message_config.get("button_text", "Вступить в Клуб")
        btn_url = message_config.get("button_url", "https://annaromeoschool.getcourse.ru/club-pay")
        
        # We will dynamically add tg_id to URL per user
        base_url = btn_url
    
    logger.info(f"🚀 Broadcasting Msg #{message_config['id']} to {len(target_users)} users...")
    
    success_count = 0
    fail_count = 0

    for user_id in target_users:
        try:
            # Add buttons if needed
            current_markup = None
            if message_config.get("buttons"):
                separator = "&" if "?" in base_url else "?"
                tracked_url = f"{base_url}{separator}tg_id={user_id}"
                current_markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=tracked_url)]])

            # Send Media or Text
            if "video_file" in message_config:
                with open(message_config["video_file"], "rb") as video:
                    await bot.send_video(chat_id=user_id, video=video, caption=text_content, parse_mode="HTML", reply_markup=current_markup)
            elif "audio_file" in message_config:
                with open(message_config["audio_file"], "rb") as audio:
                    await bot.send_audio(chat_id=user_id, audio=audio, caption=text_content, parse_mode="HTML", reply_markup=current_markup)
            else:
                 await bot.send_message(chat_id=user_id, text=text_content, parse_mode="HTML", reply_markup=current_markup)

            success_count += 1
            await asyncio.sleep(0.05) # Rate limit
            
        except Forbidden:
            # User blocked bot
            fail_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
            fail_count += 1

    logger.info(f"✅ Finished Msg #{message_config['id']}. Success: {success_count}, Failed: {fail_count}")

async def check_campaign_job():
    """Scheduled job to check if any messages need sending."""
    try:
        if not os.path.exists(CAMPAIGN_CONFIG_FILE):
            return

        try:
            with open(CAMPAIGN_CONFIG_FILE, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return

        state = load_campaign_state()
        sent_ids = set(state.get("sent_messages", []))
        
        now_utc = datetime.now(timezone.utc)
        
        for msg in config["messages"]:
            msg_id = msg["id"]
            # Parse sending time
            try:
                send_time = datetime.fromisoformat(msg["send_time_utc"]).replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.error(f"Invalid date format for msg {msg_id}: {e}")
                continue
            
            if msg_id not in sent_ids and now_utc >= send_time:
                logger.info(f"⏰ Time to send Msg #{msg_id}!")
                try:
                    await broadcast_message(msg)
                    # Mark as sent only if broadcast didn't crash
                    state["sent_messages"].append(msg_id)
                    save_campaign_state(state)
                except Exception as e:
                    logger.error(f"💥 Crashed sending Msg #{msg_id}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in check_campaign_job: {e}", exc_info=True)

if __name__ == "__main__":
    # Test run
    asyncio.run(check_campaign_job())
