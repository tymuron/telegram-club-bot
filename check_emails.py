import db
import json
import os

print("--- Supabase ---")
try:
    users = db.get_all_users()
    emails = [u.get('email') for u in users if u.get('email')]
    print(f"Total users in Supabase: {len(users)}")
    print(f"Users with email: {len(emails)}")
except Exception as e:
    print(f"Error checking Supabase: {e}")

print("\n--- JSON file ---")
if os.path.exists("subscribers.json"):
    try:
        with open("subscribers.json") as f:
            data = json.load(f)
            emails_json = [u.get('email') for u in data.values() if u.get('email')]
            print(f"Total users in JSON: {len(data)}")
            print(f"Users with email in JSON: {len(emails_json)}")
    except Exception as e:
        print(f"Error checking JSON: {e}")
