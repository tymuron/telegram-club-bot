import re
from datetime import datetime

import db

WAITLIST_FILE = "waitlist.txt"

def load_waitlist():
    users = []
    try:
        with open(WAITLIST_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                # Regex to extract data: "Name (@username) - ID: 12345"
                match = re.search(r'^(.*?) \(@(.*?)\) - ID: (\d+)', line)
                if not match:
                    # Try format "Name (No Username) - ID: 12345"
                    match = re.search(r'^(.*?) \(No Username\) - ID: (\d+)', line)
                    if match:
                        name, user_id = match.groups()
                        username = None
                        users.append({"id": int(user_id), "name": name.strip(), "username": None})
                        continue
                
                if match:
                    name, username, user_id = match.groups()
                    users.append({"id": int(user_id), "name": name.strip(), "username": username})
    except FileNotFoundError:
        print(f"❌ {WAITLIST_FILE} not found!")
    return users

def main():
    print("🚀 Starting waitlist import into Supabase...")
    
    waitlist_users = load_waitlist()
    access_ids = db.get_access_subscriber_ids()
    known_users = {u["id"] for u in db.get_all_users()}
    
    if not waitlist_users:
        print("⚠️ No users found in waitlist.txt")
        return

    print(f"📋 Found {len(waitlist_users)} in waitlist.")
    print(f"💰 Found {len(access_ids)} users with club access.")
    print(f"👥 Found {len(known_users)} existing users in Supabase.")

    added_count = 0
    skipped_paid = 0
    skipped_exists = 0

    # 2. Process
    processed_ids = set()
    
    for u in waitlist_users:
        uid = str(u['id'])
        
        # Check for duplicates in waitlist file
        if uid in processed_ids:
            print(f"⚠️ Duplicate in waitlist file: {u['name']} (ID: {uid}) - Skipping")
            continue
        processed_ids.add(uid)
        
        # Skip users who already have club access
        if u['id'] in access_ids:
            skipped_paid += 1
            print(f"⏩ Skipping {u['name']} (Already Paid)")
            continue
            
        # Skip users already known to the bot
        if u['id'] in known_users:
            skipped_exists += 1
            continue

        db.upsert_user(u['id'], {
            "first_name": u['name'],
            "username": f"@{u['username']}" if u.get('username') else "No Username",
            "status": "lead",
            "imported_from_waitlist_at": datetime.now().isoformat()
        })
        known_users.add(u['id'])
        added_count += 1
        print(f"✅ Added {u['name']} (@{u.get('username')})")

    print(f"\n🎉 IMPORT COMPLETE!")
    print(f"✅ Added {added_count} new users.")
    print(f"⏩ Skipped {skipped_paid} paid subscribers.")
    print(f"⏩ Skipped {skipped_exists} already known users.")

if __name__ == "__main__":
    main()
