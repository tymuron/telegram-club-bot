"""
Step 2 Script: Sync GetCourse CSV with Supabase

Takes a CSV exported from GetCourse (Покупки → Активна) and:
1. Matches emails against Supabase club_users
2. Creates/renews subscriptions for matched users
3. Reports unmatched emails (paid but bot doesn't know their Telegram ID)

CSV format expected: at minimum an 'email' column. 
GetCourse export usually has columns like: Номер, Продукт, Имя, Статус, Период, Email, etc.

Usage:
  python3 sync_getcourse.py active_purchases.csv
"""

import csv
import sys
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")

import db

def find_email_column(headers):
    """Find the email column in CSV headers (case-insensitive, supports Russian)."""
    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        if h_lower in ['email', 'e-mail', 'почта', 'отображаемое имя']:
            return i
        if 'email' in h_lower or 'mail' in h_lower:
            return i
    return None

def find_name_column(headers):
    """Find the name column."""
    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        if h_lower in ['имя', 'отображаемое имя', 'name', 'фио']:
            return i
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 sync_getcourse.py <path_to_csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    
    # Read CSV — GetCourse uses semicolons and utf-8
    rows = []
    headers = []
    
    for encoding in ['utf-8', 'cp1251', 'latin-1']:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f, delimiter=';')
                headers = [h.strip().strip('"') for h in next(reader)]
                rows = list(reader)
                if len(headers) > 1:
                    break
        except Exception:
            continue
    
    if not rows:
        print("❌ Could not parse CSV.")
        sys.exit(1)
    
    print(f"📄 Read {len(rows)} rows from CSV")
    print(f"   Columns: {headers}\n")
    
    # Map columns by name
    col_map = {}
    for i, h in enumerate(headers):
        h_clean = h.lower().strip()
        if 'адрес' in h_clean or 'email' in h_clean or 'mail' in h_clean:
            col_map['email'] = i
        elif h_clean in ['пользователь', 'имя', 'name']:
            col_map['name'] = i
        elif h_clean in ['статус', 'status']:
            col_map['status'] = i
    
    if 'email' not in col_map:
        print(f"❌ Could not find email column. Available: {headers}")
        sys.exit(1)
    
    print(f"   Email column: '{headers[col_map['email']]}'")
    if 'name' in col_map:
        print(f"   Name column: '{headers[col_map['name']]}'")
    if 'status' in col_map:
        print(f"   Status column: '{headers[col_map['status']]}'")
    print()
    
    # Separate active vs ended
    active_emails = []
    ended_emails = []
    
    for row in rows:
        if len(row) <= col_map['email']:
            continue
        
        email = row[col_map['email']].strip().strip('"')
        name = row[col_map.get('name', 0)].strip().strip('"') if 'name' in col_map else None
        status = row[col_map.get('status', 0)].strip().strip('"') if 'status' in col_map else 'Активна'
        
        if not email or '@' not in email:
            continue
        
        entry = {"email": email, "name": name, "gc_status": status}
        
        if status.lower() in ['активна', 'active']:
            active_emails.append(entry)
        else:
            ended_emails.append(entry)
    
    print(f"📊 GetCourse totals: {len(active_emails)} active, {len(ended_emails)} ended\n")
    
    # Process ACTIVE ones — match with Supabase
    matched_active = []
    unmatched_active = []
    renewed = 0
    
    for entry in active_emails:
        email = entry['email']
        name = entry['name']
        
        user = db.get_user_by_email(email)
        
        if user:
            user_id = user['id']
            access_sub = db.get_access_subscription(user_id)
            if access_sub:
                matched_active.append({**entry, "tg_id": user_id, "action": "already_active"})
            else:
                db.add_subscription(user_id=user_id, email=email, name=name, source='getcourse_sync')
                renewed += 1
                matched_active.append({**entry, "tg_id": user_id, "action": "renewed"})
        else:
            unmatched_active.append(entry)
    
    # Process ENDED ones — match with Supabase to mark expired
    matched_ended = []
    unmatched_ended = []
    
    for entry in ended_emails:
        email = entry['email']
        user = db.get_user_by_email(email)
        
        if user:
            user_id = user['id']
            matched_ended.append({**entry, "tg_id": user_id})
        else:
            unmatched_ended.append(entry)
    
    # === REPORT ===
    print("=" * 55)
    print(f"\n✅ ACTIVE & MATCHED (paid, bot knows them): {len(matched_active)}")
    for m in matched_active:
        icon = "🔄" if m['action'] == 'renewed' else "✅"
        print(f"   {icon} {m['name'] or m['email']} (TG: {m['tg_id']})")
    
    print(f"\n⚠️  ACTIVE but UNMATCHED (paid, bot DOESN'T know): {len(unmatched_active)}")
    for u in unmatched_active:
        print(f"   ❓ {u['name'] or '—'} ({u['email']})")
    
    print(f"\n🔴 ENDED & MATCHED (didn't renew, bot knows → CAN KICK): {len(matched_ended)}")
    for m in matched_ended:
        print(f"   🚫 {m['name'] or m['email']} (TG: {m['tg_id']})")
    
    print(f"\n⬜ ENDED & UNMATCHED (ended, bot doesn't know): {len(unmatched_ended)}")
    
    print(f"\n{'='*55}")
    print(f"📊 SUMMARY:")
    print(f"   Total in CSV:           {len(active_emails) + len(ended_emails)}")
    print(f"   Active & synced:        {len(matched_active)} (of which {renewed} renewed)")
    print(f"   Active & unmatched:     {len(unmatched_active)} ← DO NOT KICK these!")
    print(f"   Ended & can kick:       {len(matched_ended)}")
    print(f"   Ended & unknown:        {len(unmatched_ended)}")
    
    if unmatched_active:
        with open("unmatched_paid_users.txt", "w", encoding="utf-8") as f:
            f.write("# These users PAID on GetCourse but bot doesn't know their Telegram ID\n")
            f.write("# DO NOT remove them from the channel\n\n")
            for u in unmatched_active:
                f.write(f"{u['email']} — {u['name'] or 'no name'}\n")
        print(f"\n   → Saved unmatched list to unmatched_paid_users.txt")
    
    # Save whitelist
    whitelist_ids = [m['tg_id'] for m in matched_active]
    with open("whitelist_ids.txt", "w") as f:
        for tid in whitelist_ids:
            f.write(f"{tid}\n")
    print(f"   → Whitelist saved ({len(whitelist_ids)} IDs)")

if __name__ == "__main__":
    main()
