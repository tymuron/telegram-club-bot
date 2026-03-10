import csv
import db
import os
import json

from dotenv import load_dotenv
load_dotenv()

def main():
    csv_path = "/Users/annaromeo/Downloads/userproduct_export_2026-03-05_10-51-43.csv"
    
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
        
    access_emails = db.get_access_subscription_emails()
    
    getcourse_active = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row.get('Статус') == 'Активна':
                getcourse_active.append({
                    'email': row.get('Эл. адрес', '').lower().strip(),
                    'name': row.get('Пользователь', ''),
                    'expires': row.get('Заканчивается', '') 
                    # Note: We need a real expiry date, but for now we'll give them 30 days from recovery
                })
                
    lost_users = []
    for gc_user in getcourse_active:
        email = gc_user['email']
        if email not in access_emails:
            lost_users.append(gc_user)
            
    # Write to recovery JSON
    recovery_dict = {user['email']: user for user in lost_users}
    with open('recovery_list.json', 'w', encoding='utf-8') as f:
        json.dump(recovery_dict, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Generated recovery_list.json with {len(recovery_dict)} lost users.")

if __name__ == "__main__":
    main()
