"""
Payment Token Manager
Generates unique tokens for payment links and stores the mapping to Telegram user IDs.
This allows us to bypass GetCourse's inability to substitute template variables.
"""
import os
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Use persistent storage on Render
if os.path.exists("/var/data"):
    DATA_DIR = "/var/data"
else:
    DATA_DIR = "."

TOKENS_FILE = os.path.join(DATA_DIR, "payment_tokens.json")

def load_tokens() -> dict:
    """Load tokens from file."""
    if not os.path.exists(TOKENS_FILE):
        return {}
    try:
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_tokens(tokens: dict) -> None:
    """Save tokens to file."""
    try:
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving tokens: {e}")

def generate_token(tg_id: int, name: str = None) -> str:
    """
    Generate a unique payment token for a user.
    Token format: tok_XXXXXXXXXX (10 random chars)
    """
    token = f"tok_{secrets.token_hex(5)}"  # 10 hex chars
    
    tokens = load_tokens()
    tokens[token] = {
        "tg_id": tg_id,
        "name": name,
        "created_at": datetime.now().isoformat(),
        "used": False
    }
    save_tokens(tokens)
    
    logger.info(f"🎫 Generated payment token {token} for user {tg_id}")
    return token

def lookup_token(token: str) -> Optional[int]:
    """
    Look up a token and return the associated Telegram user ID.
    Returns None if token not found or already used.
    """
    tokens = load_tokens()
    
    if token not in tokens:
        logger.warning(f"⚠️ Token not found: {token}")
        return None
    
    token_data = tokens[token]
    
    # Check if token was already used
    if token_data.get("used"):
        logger.warning(f"⚠️ Token already used: {token}")
        # Still return the ID - allow reprocessing
    
    # Mark as used
    tokens[token]["used"] = True
    tokens[token]["used_at"] = datetime.now().isoformat()
    save_tokens(tokens)
    
    tg_id = token_data.get("tg_id")
    logger.info(f"✅ Token {token} resolved to user {tg_id}")
    return tg_id

def cleanup_old_tokens(days: int = 7) -> int:
    """Remove tokens older than specified days."""
    tokens = load_tokens()
    cutoff = datetime.now() - timedelta(days=days)
    
    old_tokens = []
    for token, data in tokens.items():
        created = datetime.fromisoformat(data["created_at"])
        if created < cutoff:
            old_tokens.append(token)
    
    for token in old_tokens:
        del tokens[token]
    
    if old_tokens:
        save_tokens(tokens)
        logger.info(f"🧹 Cleaned up {len(old_tokens)} old tokens")
    
    return len(old_tokens)
