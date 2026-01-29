import json
import re
import os
from datetime import datetime

# Paths
WAITLIST_FILE = "waitlist.txt"
SUBSCRIBERS_FILE = "subscribers.json"
USERS_FILE = "/var/data/users.json"  # Production path
# USERS_FILE = "users.json" # Local test path

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

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def main():
    print("🚀 Starting Waitlist Import...")
    
    # 1. Load Data
    waitlist_users = load_waitlist()
    subscribers = load_subscribers() # Dict of id -> data
    current_users = load_users()
    
    if not waitlist_users:
        print("⚠️ No users found in waitlist.txt")
        return

    print(f"📋 Found {len(waitlist_users)} in waitlist.")
    print(f"💰 Found {len(subscribers)} existing subscribers (paid).")
    print(f"👥 Found {len(current_users)} existing campaign users.")

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
        
        # Check if already paid
        if uid in subscribers:
            skipped_paid += 1
            print(f"⏩ Skipping {u['name']} (Already Paid)")
            continue
            
        # Check if already in campaign
        if uid in current_users:
            skipped_exists += 1
            # print(f"⏩ Skipping {u['name']} (Already in Campaign)")
            continue

        # Add to Campaign
        current_users[uid] = {
            "id": u['id'],
            "username": u['username'],
            "first_name": u['name'],
            "join_date": datetime.now().isoformat(),
            "funnel_start_date": datetime.now().date().isoformat(), # Start TODAY
            "funnel_step": 0,
            "last_message_id": 0,
            "finished": False, 
            "status": "active"
        }
        added_count += 1
        print(f"✅ Added {u['name']} (@{u.get('username')})")

    # 3. Save
    if added_count > 0:
        save_users(current_users)
        print(f"\n🎉 IMPORT COMPLETE!")
        print(f"✅ Added {added_count} new users.")
        print(f"⏩ Skipped {skipped_paid} paid subscribers.")
        print(f"⏩ Skipped {skipped_exists} already in campaign.")
        print(f"📈 Total Broadcast Users: {len(current_users)}")
    else:
        print("\n⚠️ No new users added.")

if __name__ == "__main__":
    main()
