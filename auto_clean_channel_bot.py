import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, EditBannedRequest
from telethon.tl.types import ChannelParticipantsRecent, ChatBannedRights
from dotenv import load_dotenv
import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Make sure CHANNEL_ID gets treated properly - it's usually negative for supergroups/channels
CHANNEL_ID = os.getenv("CHANNEL_ID")

API_ID = 6
API_HASH = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'
SESSION_NAME = 'bot_cleanup_session'

async def main():
    print("🧹 Запускаем автоматическую глубокую очистку канала клуба (от имени бота)...\n")
    
    if not CHANNEL_ID:
        print("❌ Ошибка: Не найден CHANNEL_ID в файле .env")
        return
        
    try:
        channel_id_int = int(CHANNEL_ID)
    except ValueError:
        print("❌ Ошибка: CHANNEL_ID должен быть числом")
        return

    # Keep everyone who has access (active OR grace period). Don't kick people still in grace.
    active_user_ids = db.get_access_subscriber_ids()
    
    print(f"✅ В базе данных найдено подписчиков с доступом (активных + резерв): {len(active_user_ids)}")

    # We also keep a list of admin IDs that should never be kicked.
    admin_id_str = os.getenv("ADMIN_ID", "")
    admins = {int(admin_id_str)} if admin_id_str.isdigit() else set()

    unmatched_names = set()
    try:
        with open('unmatched_paid_users.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip(): continue
                if '—' in line:
                    name = line.split('—')[1].strip().lower()
                    if name and name != 'no name':
                        unmatched_names.add(name)
        print(f"⚠️ Загружен список 'неопознанных' оплат: {len(unmatched_names)} имен")
    except FileNotFoundError:
        print("⚠️ Файл unmatched_paid_users.txt не найден, пропускаем.")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    # Login via Bot Token
    await client.start(bot_token=BOT_TOKEN)
    
    try:
        print("⏳ Сбор списка всех участников канала...")
        
        offset = 0
        limit = 100
        all_participants = []
        
        while True:
            participants = await client(GetParticipantsRequest(
                channel_id_int, ChannelParticipantsRecent(), offset, limit, hash=0
            ))
            if not participants.users:
                break
            all_participants.extend(participants.users)
            offset += len(participants.users)
            
        print(f"👥 Всего участников в канале: {len(all_participants)}\n")
        
        kicked_count = 0
        safe_count = 0
        
        banned_rights = ChatBannedRights(until_date=None, view_messages=True)
        
        print("-" * 50)
        for member in all_participants:
            # Skip bots and admins
            if member.bot or member.id in admins:
                safe_count += 1
                continue
                
            full_name = f"{member.first_name or ''} {member.last_name or ''}".strip()
            
            # Check if user has an active subscription
            if member.id in active_user_ids:
                # User has paid
                safe_count += 1
                continue
                
            # Check if they closely match an unmatched paid user
            lower_name = full_name.lower()
            is_unmatched_paid = False
            for uname in unmatched_names:
                if uname in lower_name or lower_name in uname:
                    is_unmatched_paid = True
                    break
                    
            if is_unmatched_paid:
                print(f"⚠️ Оставлен (Имя похоже на оплатившего, но бот его не знает): {full_name}")
                safe_count += 1
                continue
                
            # If they don't have an active subscription, KICK THEM
            print(f"🚫 УДАЛЕН ИЗ КАНАЛА: {full_name} (ID: {member.id}) - Нет активной подписки")
            try:
                # Ban and Unban to kick
                await client(EditBannedRequest(channel_id_int, member.id, banned_rights))
                kicked_count += 1
            except Exception as e:
                print(f"   [Ошибка при удалении {full_name}]: {e}")
                
        print("-" * 50)
        print(f"\n📊 ИТОГИ ОЧИСТКИ:")
        print(f"   Всего участников до чистки: {len(all_participants)}")
        print(f"   Удалено (нет подписки):     {kicked_count}")
        print(f"   Осталось в канале:          {safe_count}")
        print("\n✅ Готово! Бот самостоятельно очистил канал.")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
