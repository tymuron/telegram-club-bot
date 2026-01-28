
import json
import os

subs_file = "subscribers.json"
new_users = [
    {"id": 1264015279, "name": "Ирина", "username": "@IrichkaAL"},
    {"id": 452932409, "name": "Екатерина", "username": "@Ekaterinaa_Solomatina"},
    {"id": 259622921, "name": "Di", "username": "@Di_Ala"},
    {"id": 1069600264, "name": "Natasha Tukmacheva", "username": "@natasha_tukmacheva"},
    {"id": 828568605, "name": "Анна Paradigma", "username": "@anna_paradigma"}
]

try:
    with open(subs_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    print(f"Error loading: {e}")
    data = {}

added = 0
for u in new_users:
    sid = str(u["id"])
    if sid not in data:
        data[sid] = {
            "chat_id": u["id"],
            "name": u["name"],
            "status": "active",
            "manual_restore": True
        }
        added += 1
        print(f"Added {u['name']}")
    else:
        print(f"Skipped {u['name']} (Already exists)")

with open(subs_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Done. Added {added} new subscribers.")
