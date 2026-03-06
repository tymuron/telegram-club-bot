import os
from supabase import create_client
import sys

# Try matching .env logic from db.py
try:
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            key, val = line.split("=", 1)
            os.environ[key] = val
except Exception as e:
    print(f"Error reading .env: {e}")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("MISSING URL OR KEY!")
    sys.exit(1)

client = create_client(url, key)

ids = [583818140, 1264015279, 346912809, 1686161167]
res = client.table("club_users").select("first_name,email").in_("id", ids).execute()

for u in res.data:
    em = u.get("email")
    print(u.get("first_name"), "->", em if em else "WAITING FOR EMAIL INPUT")
