
import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
TEST_USER_ID = 1873528397

async def send_test():
    bot = Bot(token=BOT_TOKEN)
    
    print("Testing VIDEO broadcast...")
    try:
        with open("media/video_msg3.mp4", "rb") as f:
            await bot.send_video(chat_id=TEST_USER_ID, video=f, caption="🎥 TEST: Message 3 Video")
        print("✅ Video Sent!")
    except Exception as e:
        print(f"❌ Video Failed: {e}")

    print("Testing VOICE broadcast...")
    try:
        with open("media/voice_msg7.m4a", "rb") as f:
            await bot.send_audio(chat_id=TEST_USER_ID, audio=f, caption="🎤 TEST: Message 7 Voice")
        print("✅ Voice Sent!")
    except Exception as e:
        print(f"❌ Voice Failed: {e}")

asyncio.run(send_test())
