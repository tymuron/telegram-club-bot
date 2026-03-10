import os
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import GetAdminLogRequest
from telethon.tl.types import ChannelAdminLogEventsFilter
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ID = os.getenv("CHANNEL_ID")
API_ID = 6
API_HASH = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'
SESSION_NAME = 'admin_cleanup_session'
BOT_TOKEN = os.getenv("BOT_TOKEN")
import db

async def main():
    if not CHANNEL_ID:
        print("No CHANNEL_ID")
        return
        
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    kicked_users = set()
    try:
        channel_id_int = int(CHANNEL_ID)
        
        print("Fetching recent kicks from admin log...")
        filter = ChannelAdminLogEventsFilter(kick=True)
        result = await client(GetAdminLogRequest(
            channel=channel_id_int,
            q="",
            min_id=0,
            max_id=0,
            limit=200,
            events_filter=filter,
            admins=[]
        ))
        
        for event in result.events:
            # Check if this is a ban event from today
            kicked_users.add(event.user_id)
            
        print(f"Found {len(kicked_users)} recently kicked users in the admin log.")
        
        with open('kicked_backup.txt', 'w') as f:
            for uid in kicked_users:
                f.write(f"{uid}\n")
                
    except Exception as e:
        print(f"Error fetching logs: {e}")
        await client.disconnect()
        return
        
    await client.disconnect()

    # Phase 2: Use bot to send them invite links
    print("Using Bot to send rescue links...")
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    
    success = 0
    failed = 0
    skipped_no_access = 0
    try:
        for uid in kicked_users:
            try:
                if not db.has_channel_access(uid):
                    skipped_no_access += 1
                    print(f"⏩ Skipping {uid}: no active/grace access in Supabase")
                    continue

                invite = await bot.create_chat_invite_link(
                    chat_id=CHANNEL_ID,
                    member_limit=1,
                    name=f"Rescue {uid}"
                )
                await bot.send_message(
                    chat_id=uid,
                    text=f"❗️ <b>Техническая ошибка</b>\n\nДобрый день! Прошу прощения, наш бот случайно удалил некоторых участников клуба из-за сбоя в синхронизации оплат с GetCourse.\n\nПожалуйста, вернитесь в канал по этой индивидуальной ссылке: {invite.invite_link}\n\nЕще раз извините за неудобства! Ваша подписка в системе активна.",
                    parse_mode="HTML"
                )
                success += 1
                print(f"✅ Sent message to {uid}")
            except Exception as e:
                failed += 1
                print(f"❌ Could not DM {uid}: {e}")
                
    except Exception as e:
        print(f"Bot error: {e}")
        
    print(f"\nRescue Results:\nSent DMs: {success}\nFailed DMs (User never started bot): {failed}\nSkipped (no access in Supabase): {skipped_no_access}")

if __name__ == "__main__":
    asyncio.run(main())
