
import json
import re

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
subscribers_file = "subscribers.json"

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

# Save to subscribers.json
existing_subs = {}
try:
    with open(subscribers_file, "r") as f:
        existing_subs = json.load(f)
except:
    pass

for f in found:
    existing_subs[str(f['id'])] = {
        "chat_id": f['id'],
        "name": f['name'],
        "status": "active",
        "restored": True
    }

with open(subscribers_file, "w", encoding="utf-8") as f:
    json.dump(existing_subs, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved {len(existing_subs)} subscribers to {subscribers_file}")
