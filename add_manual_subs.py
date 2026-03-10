import db

new_users = [
    {"id": 1264015279, "name": "Ирина", "username": "@IrichkaAL"},
    {"id": 452932409, "name": "Екатерина", "username": "@Ekaterinaa_Solomatina"},
    {"id": 259622921, "name": "Di", "username": "@Di_Ala"},
    {"id": 1069600264, "name": "Natasha Tukmacheva", "username": "@natasha_tukmacheva"},
    {"id": 828568605, "name": "Анна Paradigma", "username": "@anna_paradigma"}
]

added = 0
for u in new_users:
    if not db.has_channel_access(u["id"]):
        db.upsert_user(u["id"], {
            "first_name": u["name"],
            "username": u["username"],
            "status": "lead",
        })
        db.add_subscription(
            user_id=u["id"],
            name=u["name"],
            source="manual_restore",
        )
        added += 1
        print(f"Added {u['name']}")
    else:
        print(f"Skipped {u['name']} (Already has access)")

print(f"Done. Added {added} new subscribers.")
