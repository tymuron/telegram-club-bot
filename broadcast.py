
import os
import asyncio
import re
import json
import logging
import sys
import glob
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

SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
# Fallback to repo file
if not os.path.exists(SUBSCRIBERS_FILE):
    SUBSCRIBERS_FILE = "subscribers.json"

USERS_FILE = os.path.join(DATA_DIR, "users.json")

# Logging functionality
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================
# TARGET LOADING FUNCTIONS
# ============================================

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


def load_subscribers_data():
    """Load full subscriber data dict."""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load subscribers: {e}")
    return {}


def load_users_data():
    """Load users.json database."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load users.json: {e}")
    return {}


def load_target_users_non_subscribers():
    """Load users from users.json (active funnel) who have NOT paid."""
    subscriber_ids = load_subscriber_ids()
    target_users = set()
    
    # 1. Try loading from users.json (The Database)
    users = load_users_data()
    for uid, user_data in users.items():
        user_id = int(uid)
        if user_id not in subscriber_ids and user_data.get("status") != "blocked":
            target_users.add(user_id)
    
    if target_users:
        logger.info(f"Loaded {len(target_users)} active users from DB.")

    # 2. Merge with waitlist.txt (Legacy/New Leads)
    if os.path.exists(WAITLIST_FILE):
        try:
            with open(WAITLIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    match = re.search(r"ID:\s*(\d+)", line)
                    if match:
                        user_id = int(match.group(1))
                        if user_id not in subscriber_ids:
                            target_users.add(user_id)
        except Exception as e:
            logger.error(f"Error reading waitlist: {e}")
        
    return target_users


def load_target_users_reminded():
    """Load users who clicked 'Напомнить мне 1 марта' (remind_march=true in users.json)."""
    users = load_users_data()
    subscriber_ids = load_subscriber_ids()
    target_users = set()
    
    for uid, user_data in users.items():
        user_id = int(uid)
        if (user_data.get("remind_march") and 
            user_id not in subscriber_ids and 
            user_data.get("status") != "blocked"):
            target_users.add(user_id)
    
    logger.info(f"Loaded {len(target_users)} reminded users.")
    return target_users


def load_target_subscribers_not_renewed():
    """Load active subscribers who haven't renewed for March yet.
    
    A subscriber is 'not renewed' if their paid_at is before March 1, 2026.
    Once they renew, their paid_at will update to a date in March, excluding them.
    """
    subs = load_subscribers_data()
    march_1 = datetime(2026, 3, 1)
    target_users = set()
    
    for chat_id, data in subs.items():
        if data.get("status") != "active":
            continue
        
        paid_at_str = data.get("paid_at")
        if not paid_at_str:
            # Subscribers without paid_at (restored manually) — include them
            target_users.add(int(chat_id))
            continue
            
        try:
            paid_at = datetime.fromisoformat(paid_at_str)
            if paid_at < march_1:
                # Hasn't renewed yet for March
                target_users.add(int(chat_id))
        except Exception:
            target_users.add(int(chat_id))
    
    logger.info(f"Loaded {len(target_users)} subscribers needing renewal.")
    return target_users


def get_target_users_for_campaign(target_type):
    """Get target users based on campaign target type."""
    if target_type == "non_subscribers":
        return load_target_users_non_subscribers()
    elif target_type == "reminded":
        return load_target_users_reminded()
    elif target_type == "active_subscribers_not_renewed":
        return load_target_subscribers_not_renewed()
    else:
        logger.warning(f"Unknown target type: {target_type}, falling back to non_subscribers")
        return load_target_users_non_subscribers()


# ============================================
# CAMPAIGN STATE MANAGEMENT
# ============================================

def get_state_file(campaign_id):
    """Get the state file path for a specific campaign."""
    return os.path.join(DATA_DIR, f"campaign_state_{campaign_id}.json")


def load_campaign_state(campaign_id):
    state_file = get_state_file(campaign_id)
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except:
            return {"sent_messages": []}
    return {"sent_messages": []}


def save_campaign_state(campaign_id, state):
    state_file = get_state_file(campaign_id)
    try:
        with open(state_file, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Failed to save state for {campaign_id}: {e}")


# ============================================
# BROADCAST LOGIC
# ============================================

async def broadcast_message(message_config, target_users):
    """Send a specific message to target users."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN missing")
        return

    bot = Bot(token=BOT_TOKEN)
    
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
    btn_text = None
    base_url = None
    if message_config.get("buttons"):
        btn_text = message_config.get("button_text", "Вступить в Клуб")
        base_url = message_config.get("button_url", "https://annaromeoschool.getcourse.ru/club-pay")
    
    has_support_button = message_config.get("support_button", False)
    
    logger.info(f"🚀 Broadcasting Msg #{message_config['id']} to {len(target_users)} users...")
    
    success_count = 0
    fail_count = 0

    for user_id in target_users:
        try:
            # Build keyboard
            current_markup = None
            keyboard_rows = []
            
            if btn_text and base_url:
                separator = "&" if "?" in base_url else "?"
                tracked_url = f"{base_url}{separator}tg_id={user_id}"
                keyboard_rows.append([InlineKeyboardButton(btn_text, url=tracked_url)])
            
            if has_support_button:
                keyboard_rows.append([InlineKeyboardButton("Написать в поддержку", url="https://t.me/tymuron")])
            
            if keyboard_rows:
                current_markup = InlineKeyboardMarkup(keyboard_rows)

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


async def process_campaign(config_file):
    """Process a single campaign config file."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Error loading config {config_file}: {e}")
        return
    
    campaign_id = config.get("campaign_id", os.path.basename(config_file))
    target_type = config.get("target", "non_subscribers")
    
    state = load_campaign_state(campaign_id)
    sent_ids = set(state.get("sent_messages", []))
    
    now_utc = datetime.now(timezone.utc)
    
    for msg in config.get("messages", []):
        msg_id = msg["id"]
        
        # Parse sending time
        try:
            send_time = datetime.fromisoformat(msg["send_time_utc"]).replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.error(f"Invalid date format for msg {msg_id}: {e}")
            continue
        
        if msg_id not in sent_ids and now_utc >= send_time:
            logger.info(f"⏰ Time to send Msg #{msg_id} from campaign '{campaign_id}'!")
            try:
                # Get target users fresh for each message (important for renewal — user may have renewed between messages)
                target_users = get_target_users_for_campaign(target_type)
                await broadcast_message(msg, target_users)
                # Mark as sent
                state["sent_messages"].append(msg_id)
                save_campaign_state(campaign_id, state)
            except Exception as e:
                logger.error(f"💥 Crashed sending Msg #{msg_id}: {e}", exc_info=True)


async def check_campaign_job():
    """Scheduled job to check if any messages need sending across ALL campaigns."""
    try:
        # Find all campaign config files
        config_files = glob.glob("campaign_config*.json")
        
        if not config_files:
            return
        
        for config_file in config_files:
            await process_campaign(config_file)

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in check_campaign_job: {e}", exc_info=True)


if __name__ == "__main__":
    # Test run
    asyncio.run(check_campaign_job())
