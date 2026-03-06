import os
import db

def test():
    print(f"URL from env: {os.environ.get('SUPABASE_URL')}")
    client = db.get_client()
    if client:
        try:
            res = client.table("club_users").select("email").neq("email", "null").execute()
            emails = [r['email'] for r in res.data if r.get('email')]
            print(f"Total emails in Supabase: {len(emails)}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No client")

test()
