
import asyncio
import os
import json
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
TEST_USER_ID = 1873528397
CONFIG_FILE = "campaign_config.json"

async def preview_broadcast():
    bot = Bot(token=BOT_TOKEN)
    
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)["messages"]

    # We will preview Message 3 (Video) and Message 7 (Voice) as requested
    # And maybe Message 1 just to show a text+button example
    ids_to_preview = [3, 7] 
    
    print(f"🚀 Sending previews for Messages {ids_to_preview} to ID {TEST_USER_ID}...")

    for msg in config:
        if msg["id"] in ids_to_preview:
            print(f"\n--- Previewing Message {msg['id']} ---")
            
            # Load actual text
            text_content = ""
            if "text_file" in msg:
                try:
                    with open(msg["text_file"], "r", encoding="utf-8") as f:
                        text_content = f.read()
                except Exception as e:
                    text_content = f"[ERROR READING FILE]: {e}"

            # Prepare Buttons
            reply_markup = None
            if msg.get("buttons"):
                btn_text = msg.get("button_text", "Вступить в Клуб")
                btn_url = msg.get("button_url", "https://annaromeoschool.getcourse.ru/club-pay")
                # Add test tracking
                tracked_url = f"{btn_url}?tg_id={TEST_USER_ID}"
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=tracked_url)]])

            # Send
            try:
                if "video_file" in msg:
                    with open(msg["video_file"], "rb") as f:
                        await bot.send_video(chat_id=TEST_USER_ID, video=f, caption=text_content, parse_mode="HTML", reply_markup=reply_markup)
                elif "audio_file" in msg:
                    with open(msg["audio_file"], "rb") as f:
                        await bot.send_audio(chat_id=TEST_USER_ID, audio=f, caption=text_content, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    await bot.send_message(chat_id=TEST_USER_ID, text=text_content, parse_mode="HTML", reply_markup=reply_markup)
                
                print(f"✅ Sent Message {msg['id']}")
            except Exception as e:
                print(f"❌ Failed Message {msg['id']}: {e}")

if __name__ == "__main__":
    asyncio.run(preview_broadcast())
