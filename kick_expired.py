"""
Standalone Mass-Kick Script
Run this locally to kick ALL expired subscribers from the Telegram channel.

Usage: 
  export $(grep -v '^#' .env | xargs)
  export SUPABASE_URL=... SUPABASE_KEY=...
  python3 kick_expired.py
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PAYMENT_LINK = os.getenv("PAYMENT_LINK")

import db

async def mass_kick():
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    
    bot = Bot(token=BOT_TOKEN)
    
    expired = db.get_all_expired_and_overdue()
    
    if not expired:
        print("✅ No expired subscriptions found. All good!")
        return
    
    print(f"🔍 Found {len(expired)} expired subscriptions. Starting kick process...\n")
    
    kicked = 0
    failed = 0
    already_gone = 0
    
    renew_markup = None
    if PAYMENT_LINK:
        renew_markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ ПРОДЛИТЬ ПОДПИСКУ", url=PAYMENT_LINK)]])
    
    for sub in expired:
        user_id = sub['user_id']
        name = sub.get('name') or sub.get('email') or str(user_id)
        
        # Send expiry notice
        try:
            await bot.send_message(
                chat_id=user_id,
                text=db.EXPIRY_WARNING_TEXT,
                reply_markup=renew_markup
            )
        except Exception:
            pass  # User may have blocked the bot
        
        # Kick from channel
        if CHANNEL_ID:
            try:
                await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                await bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                kicked += 1
                print(f"  🚫 Kicked: {name} (ID: {user_id})")
            except Exception as e:
                err_str = str(e).lower()
                if 'user not found' in err_str or 'not a member' in err_str or 'participant_id_invalid' in err_str:
                    already_gone += 1
                    print(f"  👻 Already gone: {name} (ID: {user_id})")
                else:
                    failed += 1
                    print(f"  ❌ Failed: {name} (ID: {user_id}) — {e}")
        
        # Mark expired in DB
        db.mark_expired(user_id)
    
    print(f"\n{'='*40}")
    print(f"✅ DONE")
    print(f"🚫 Kicked from channel: {kicked}")
    print(f"👻 Already not in channel: {already_gone}")
    print(f"❌ Errors: {failed}")
    print(f"📊 Total processed: {len(expired)}")

if __name__ == "__main__":
    asyncio.run(mass_kick())
