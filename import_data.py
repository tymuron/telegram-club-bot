"""
One-time import script: Migrate existing subscribers.json and users.json → Supabase.
Run this locally after setting SUPABASE_URL and SUPABASE_KEY in .env.

Usage:
    python import_data.py
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()

import db


def import_subscribers():
    """Import subscribers.json to Supabase."""
    # Try persistent path first, then local
    for path in ["/var/data/subscribers.json", "subscribers.json"]:
        if os.path.exists(path):
            print(f"📥 Found {path}")
            with open(path, "r", encoding="utf-8") as f:
                subs = json.load(f)
            
            count = 0
            for chat_id_str, data in subs.items():
                try:
                    user_id = int(chat_id_str)
                    
                    # Upsert user first
                    db.upsert_user(user_id, {
                        "first_name": data.get("name", ""),
                        "email": data.get("email", ""),
                        "status": "lead",
                    })
                    
                    # Add subscription
                    db.add_subscription(
                        user_id=user_id,
                        email=data.get("email"),
                        name=data.get("name"),
                        source="import",
                    )
                    
                    count += 1
                    print(f"  ✅ Imported subscriber {user_id} ({data.get('name', 'unknown')})")
                except Exception as e:
                    print(f"  ❌ Failed to import {chat_id_str}: {e}")
            
            print(f"\n📊 Imported {count}/{len(subs)} subscribers.")
            return
    
    print("⚠️ No subscribers.json found.")


def import_users():
    """Import users.json to Supabase."""
    for path in ["/var/data/users.json", "users.json"]:
        if os.path.exists(path):
            print(f"📥 Found {path}")
            with open(path, "r", encoding="utf-8") as f:
                users = json.load(f)
            
            count = 0
            for user_id_str, data in users.items():
                try:
                    user_id = int(user_id_str)
                    
                    db.upsert_user(user_id, {
                        "first_name": data.get("first_name", ""),
                        "last_name": data.get("last_name", ""),
                        "username": data.get("username", ""),
                        "remind_march": data.get("remind_march", False),
                        "status": "lead",
                    })
                    
                    count += 1
                    print(f"  ✅ Imported user {user_id}")
                except Exception as e:
                    print(f"  ❌ Failed to import {user_id_str}: {e}")
            
            print(f"\n📊 Imported {count}/{len(users)} users.")
            return
    
    print("⚠️ No users.json found.")


if __name__ == "__main__":
    print("=" * 50)
    print("Supabase Data Import")
    print("=" * 50)
    
    if not db.get_client():
        print("❌ Supabase connection failed. Check SUPABASE_URL and SUPABASE_KEY in .env")
        exit(1)
    
    print("\n--- Importing Users ---")
    import_users()
    
    print("\n--- Importing Subscribers ---")
    import_subscribers()
    
    print("\n✅ Import complete!")
