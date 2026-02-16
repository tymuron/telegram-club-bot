
import os
import asyncio
import json
import logging
import glob
from datetime import datetime, timezone
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, BadRequest

# Import our database layer
import db

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================
# TARGET LOADING FUNCTIONS
# ============================================

def get_target_users_for_campaign(target_type):
    """Get target users based on campaign target type."""
    if target_type == "non_subscribers":
        return db.get_non_subscriber_ids()
    elif target_type == "reminded":
        return db.get_reminded_user_ids()
    elif target_type == "active_subscribers_not_renewed":
        return db.get_subscribers_not_renewed()
    else:
        logger.warning(f"Unknown target type: {target_type}, falling back to non_subscribers")
        return db.get_non_subscriber_ids()


# ============================================
# BROADCAST LOGIC
# ============================================

async def broadcast_message(message_config, target_users):
    """Send a specific message to target users."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN missing")
        return 0, 0

    bot = Bot(token=BOT_TOKEN)
    
    if not target_users:
        logger.info("No target users for broadcast.")
        return 0, 0

    # Load Text
    text_content = ""
    if "text_file" in message_config:
        try:
            with open(message_config["text_file"], "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            logger.error(f"Could not read message file: {e}")
            return 0, 0

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
            # User blocked bot — mark in DB
            db.upsert_user(user_id, {"status": "blocked"})
            fail_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
            fail_count += 1

    logger.info(f"✅ Finished Msg #{message_config['id']}. Success: {success_count}, Failed: {fail_count}")
    return success_count, fail_count


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
    
    # Get already-sent messages from Supabase
    sent_ids = db.get_sent_campaign_messages(campaign_id)
    
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
                # Get target users fresh for each message
                target_users = get_target_users_for_campaign(target_type)
                success, fail = await broadcast_message(msg, target_users)
                
                # Mark as sent in Supabase
                db.mark_campaign_message_sent(
                    campaign_id=campaign_id,
                    message_id=msg_id,
                    target_count=len(target_users),
                    success_count=success
                )
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
            # Skip backup files
            if config_file.endswith('.bak'):
                continue
            await process_campaign(config_file)

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in check_campaign_job: {e}", exc_info=True)


if __name__ == "__main__":
    # Test run
    asyncio.run(check_campaign_job())
