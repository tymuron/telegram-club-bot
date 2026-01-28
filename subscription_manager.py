"""
Subscription Manager Module
Handles:
- Webhook endpoint for GetCourse payment notifications
- Subscriber database (JSON)
- Scheduled reminders (Day 27)
- Auto-kick on expiration (Day 30+)
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Configuration
# Use persistent disk path on Render if available, else local file
if os.path.exists("/var/data"):
    DATA_DIR = "/var/data"
else:
    DATA_DIR = "."

SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")

# On first run, copy repo's subscribers.json to persistent storage if not exists
if DATA_DIR == "/var/data" and not os.path.exists(SUBSCRIBERS_FILE):
    REPO_SUBSCRIBERS = "subscribers.json"  # File in repo root
    if os.path.exists(REPO_SUBSCRIBERS):
        import shutil
        shutil.copy(REPO_SUBSCRIBERS, SUBSCRIBERS_FILE)
        logger.info(f"📋 Copied initial subscribers from repo to {SUBSCRIBERS_FILE}")

REMINDER_DAY = 27  # Days after payment to send reminder
EXPIRY_DAY = 30    # Days after payment when subscription expires
GRACE_PERIOD = 3   # Extra days before kicking

# --- Database Functions ---
def load_subscribers() -> Dict:
    """Load subscribers from JSON file."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {}
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading subscribers: {e}")
        return {}

def save_subscribers(data: Dict) -> None:
    """Save subscribers to JSON file."""
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving subscribers: {e}")

def add_subscriber(chat_id: int, email: str = None, name: str = None) -> None:
    """Add or update a subscriber after successful payment."""
    subs = load_subscribers()
    now = datetime.now()
    
    subs[str(chat_id)] = {
        "chat_id": chat_id,
        "email": email,
        "name": name,
        "paid_at": now.isoformat(),
        "expires_at": (now + timedelta(days=EXPIRY_DAY)).isoformat(),
        "status": "active",
        "reminder_sent": False,
        "renewed_count": subs.get(str(chat_id), {}).get("renewed_count", 0) + 1
    }
    
    save_subscribers(subs)
    logger.info(f"✅ Subscriber added/renewed: {chat_id} ({name or email})")

def mark_expired(chat_id: int) -> None:
    """Mark a subscriber as expired."""
    subs = load_subscribers()
    if str(chat_id) in subs:
        subs[str(chat_id)]["status"] = "expired"
        save_subscribers(subs)

def mark_reminder_sent(chat_id: int) -> None:
    """Mark that reminder was sent."""
    subs = load_subscribers()
    if str(chat_id) in subs:
        subs[str(chat_id)]["reminder_sent"] = True
        save_subscribers(subs)

def get_subscribers_needing_reminder() -> List[Dict]:
    """Get subscribers who are at Day 27 and haven't received reminder."""
    subs = load_subscribers()
    result = []
    now = datetime.now()
    
    for chat_id, data in subs.items():
        if data.get("status") != "active":
            continue
        if data.get("reminder_sent"):
            continue
            
        paid_at = datetime.fromisoformat(data["paid_at"])
        days_since = (now - paid_at).days
        
        if days_since >= REMINDER_DAY:
            result.append(data)
    
    return result

def get_expired_subscribers() -> List[Dict]:
    """Get subscribers who have passed expiry + grace period."""
    subs = load_subscribers()
    result = []
    now = datetime.now()
    
    for chat_id, data in subs.items():
        if data.get("status") != "active":
            continue
            
        expires_at = datetime.fromisoformat(data["expires_at"])
        grace_end = expires_at + timedelta(days=GRACE_PERIOD)
        
        if now > grace_end:
            result.append(data)
    
    return result

def get_all_active_subscribers() -> List[Dict]:
    """Get all active subscribers for admin report."""
    subs = load_subscribers()
    return [s for s in subs.values() if s.get("status") == "active"]

def get_all_subscribers() -> Dict:
    """Get all subscribers (raw dict for API)."""
    return load_subscribers()

# --- Webhook Payload Parser ---
def parse_getcourse_webhook(data: dict) -> Optional[Dict]:
    """
    Parse GetCourse webhook payload.
    Returns: {chat_id, email, name, payment_status}
    
    GetCourse webhook typically sends:
    - user email
    - order status
    - UTM parameters (where we hide chat_id)
    """
    try:
        # GetCourse sends different structures, we adapt
        # Look for our tg_id in UTM params or custom fields
        
        # Option 1: From UTM source (if we embedded it in payment link)
        utm_params = data.get("utm", {})
        tg_id = utm_params.get("tg_id") or data.get("tg_id")
        
        # Option 2: From custom field (if user entered)
        fields = data.get("fields", {})
        if not tg_id:
            tg_id = fields.get("telegram_id")
        
        # Email is usually straightforward
        email = data.get("email") or data.get("user", {}).get("email")
        name = data.get("name") or data.get("user", {}).get("name")
        
        # Status
        status = data.get("status") or data.get("order_status")
        
        return {
            "chat_id": int(tg_id) if tg_id else None,
            "email": email,
            "name": name,
            "status": status
        }
    except Exception as e:
        logger.error(f"Error parsing webhook: {e}")
        return None

# --- Reminder Text ---
REMINDER_TEXT = """⏰ <b>Напоминание о подписке</b>

Привет! Ваша подписка на Клуб «Точка Опоры» продлится через <b>3 дня</b>.

Если у вас включен автоплатёж — всё произойдёт автоматически. 
Если нет — не забудьте продлить, чтобы не потерять доступ.

💳 Остались вопросы? Напишите @tymuron
"""

EXPIRY_WARNING_TEXT = """⚠️ <b>Подписка истекла</b>

К сожалению, ваша подписка на Клуб «Точка Опоры» закончилась.

Чтобы продолжить получать материалы и оставаться в нашем кругу, пожалуйста, продлите подписку.

💳 Продлить: {payment_link}

Будем рады видеть вас снова! 🤗
"""
