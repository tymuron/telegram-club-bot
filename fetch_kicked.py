import os
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, EditBannedRequest
from telethon.tl.types import ChannelParticipantsKicked, ChatBannedRights
from dotenv import load_dotenv
import time

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_ID = 6
API_HASH = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'
SESSION_NAME = 'bot_rescue_session'

import db

async def main():
    channel_id_int = int(CHANNEL_ID)
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    try:
        print("Fetching kicked participants...")
        offset = 0
        limit = 100
        banned_users = []
        
        while True:
            participants = await client(GetParticipantsRequest(
                channel_id_int, ChannelParticipantsKicked(""), offset, limit, hash=0
            ))
            if not participants.users:
                break
            banned_users.extend(participants.users)
            offset += len(participants.users)
            
        print(f"Found {len(banned_users)} banned users.")
        
        with open('banned_users.txt', 'w') as f:
            for u in banned_users:
                f.write(f"{u.id},{u.first_name},{u.last_name}\n")
                
        # Now, unban access-valid users and send invite links
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)

        success = 0
        failed = 0
        skipped_no_access = 0
        
        empty_rights = ChatBannedRights(
            until_date=None,
            view_messages=False,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False
        )
        
        for u in banned_users:
            try:
                if not db.has_channel_access(u.id):
                    skipped_no_access += 1
                    print(f"⏩ Skipping {u.first_name}: no active/grace access in Supabase")
                    continue

                # 1. Unban them
                await client(EditBannedRequest(channel_id_int, u.id, empty_rights))

                # 2. Create a fresh personal rescue invite
                invite = await bot.create_chat_invite_link(
                    chat_id=CHANNEL_ID,
                    member_limit=1,
                    name=f"Rescue {u.id}"
                )

                # 3. Message them
                await bot.send_message(
                    chat_id=u.id,
                    text=f"❗️ <b>Техническая ошибка</b>\n\nДобрый день! Прошу прощения, наш бот случайно удалил некоторых участников клуба из-за сбоя в синхронизации оплат с GetCourse.\n\nПожалуйста, вернитесь в канал по этой индивидуальной ссылке: {invite.invite_link}\n\nЕще раз извините за неудобства! Ваша подписка в системе активна.",
                    parse_mode="HTML"
                )
                success += 1
                print(f"✅ Restored and messaged {u.first_name}")
            except Exception as e:
                failed += 1
                print(f"❌ Unban/Msg failed for {u.first_name}: {e}")
                
            await asyncio.sleep(0.1) # rate limit
            
        print(f"Finished. DMs sent: {success}, Failed DMs: {failed}, Skipped (no access in Supabase): {skipped_no_access}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

asyncio.run(main())
