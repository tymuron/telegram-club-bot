
import re
import db

# List of paid names from screenshots
paid_names = [
    "Алина",
    "Ирина Аметова",
    "Елена",
    "Анастасия",
    "Оксана",
    "Наталья",
    "Малика",
    "Ксения",
    "Светлана",
    "Алена",
    "Евгения Белашова",
    "Кристина",
    "Екатерина Уханова",
    "Динара Жартыбаева",
    "Natasha Tukmacheva",
    "Анна Неволина",
    "GülÖzmüs"
]

waitlist_file = "waitlist.txt"
# Load waitlist
waitlist_users = []
try:
    with open(waitlist_file, "r", encoding="utf-8") as f:
        for line in f:
            # Parse line: "Name Lastname (@user) - ID: 123"
            try:
                parts = line.split(" - ID: ")
                if len(parts) == 2:
                    raw_name = parts[0].strip()
                    user_id = int(parts[1].strip())
                    
                    # Clean name (remove @username)
                    clean_name = re.sub(r'\s*\(@.*?\)', '', raw_name).strip()
                    username_match = re.search(r'\(@(.*?)\)', raw_name)
                    username = username_match.group(1) if username_match else ""
                    
                    waitlist_users.append({
                        "id": user_id,
                        "raw": raw_name,
                        "clean_name": clean_name,
                        "username": username
                    })
            except:
                continue
except FileNotFoundError:
    print("Waitlist file not found.")

# Match Logic
found = []
not_found = []

for paid in paid_names:
    match = None
    # 1. Exact match
    for user in waitlist_users:
        if paid.lower() in user['clean_name'].lower() or user['clean_name'].lower() in paid.lower():
             match = user
             break
    
    if match:
        found.append({"name": paid, "id": match['id'], "telegram_name": match['clean_name']})
    else:
        not_found.append(paid)

print(f"✅ MATCHED: {len(found)}")
for f in found:
    print(f"  - {f['name']} -> {f['telegram_name']} (ID: {f['id']})")

print(f"\n❌ NOT FOUND: {len(not_found)}")
for n in not_found:
    print(f"  - {n}")

added = 0
for f in found:
    if db.has_channel_access(f['id']):
        print(f"⏩ Already has access: {f['name']} ({f['id']})")
        continue
    db.upsert_user(f['id'], {
        "first_name": f['telegram_name'],
        "status": "lead",
    })
    db.add_subscription(
        user_id=f['id'],
        name=f['name'],
        source="manual_restore",
    )
    added += 1

print(f"\n💾 Restored {added} matched subscribers into Supabase")
