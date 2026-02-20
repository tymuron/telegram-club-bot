"""
Database Layer — Supabase wrapper for Club Bot
Replaces all JSON file operations with Supabase queries.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Use service_role key (not anon)

# Graceful fallback if Supabase not configured
_client = None

def get_client():
    """Lazy-init Supabase client."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("❌ SUPABASE_URL or SUPABASE_KEY not set!")
            return None
        try:
            from supabase import create_client
            _client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("✅ Supabase connected")
        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
            return None
    return _client


# ============================================
# USER OPERATIONS
# ============================================

def upsert_user(user_id: int, data: dict) -> bool:
    """Create or update a user record."""
    client = get_client()
    if not client:
        return False
    try:
        record = {"id": user_id, **data}
        client.table("club_users").upsert(record, on_conflict="id").execute()
        return True
    except Exception as e:
        logger.error(f"Error upserting user {user_id}: {e}")
        return False


def get_user(user_id: int) -> Optional[Dict]:
    """Get a single user by Telegram ID."""
    client = get_client()
    if not client:
        return None
    try:
        result = client.table("club_users").select("*").eq("id", user_id).maybe_single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Find a user by email (for GetCourse fallback matching)."""
    client = get_client()
    if not client or not email:
        return None
    try:
        result = client.table("club_users").select("*").ilike("email", email.strip()).maybe_single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Error finding user by email: {e}")
        return None


def get_all_users() -> List[Dict]:
    """Get all users."""
    client = get_client()
    if not client:
        return []
    try:
        result = client.table("club_users").select("*").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []


# ============================================
# SUBSCRIPTION OPERATIONS
# ============================================

EXPIRY_DAYS = 30
REMINDER_DAY = 27
GRACE_DAYS = 3  # 3 days grace after expiry before kicking (awaiting late recurring webhooks)


def add_subscription(user_id: int, email: str = None, name: str = None, 
                     source: str = "getcourse") -> bool:
    """Add a new subscription (payment received)."""
    client = get_client()
    if not client:
        return False
    try:
        now = datetime.now()
        expires = now + timedelta(days=EXPIRY_DAYS)
        
        # First ensure user exists
        upsert_user(user_id, {
            "status": "lead",
            "email": email,
        })
        
        # Expire any previous active subscription
        client.table("club_subscriptions") \
            .update({"status": "expired"}) \
            .eq("user_id", user_id) \
            .eq("status", "active") \
            .execute()
        
        # Count previous subscriptions for renewed_count
        prev = client.table("club_subscriptions") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()
        renewed_count = (prev.count or 0) + 1
        
        # Insert new subscription
        client.table("club_subscriptions").insert({
            "user_id": user_id,
            "paid_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "status": "active",
            "reminder_sent": False,
            "payment_source": source,
            "renewed_count": renewed_count,
            "email": email,
            "name": name,
        }).execute()
        
        logger.info(f"✅ Subscription added: user {user_id} (renewal #{renewed_count})")
        return True
    except Exception as e:
        logger.error(f"Error adding subscription for {user_id}: {e}")
        return False


def get_active_subscription(user_id: int) -> Optional[Dict]:
    """Get user's current active subscription."""
    client = get_client()
    if not client:
        return None
    try:
        result = client.table("club_subscriptions") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("status", "active") \
            .order("paid_at", desc=True) \
            .limit(1) \
            .maybe_single() \
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting subscription for {user_id}: {e}")
        return None


def is_active_subscriber(user_id: int) -> bool:
    """Check if user has an active subscription."""
    sub = get_active_subscription(user_id)
    return sub is not None


def get_subscribers_needing_reminder() -> List[Dict]:
    """Get active subscribers at or past REMINDER_DAY who haven't been reminded."""
    client = get_client()
    if not client:
        return []
    try:
        cutoff = (datetime.now() - timedelta(days=REMINDER_DAY)).isoformat()
        result = client.table("club_subscriptions") \
            .select("*") \
            .eq("status", "active") \
            .eq("reminder_sent", False) \
            .lte("paid_at", cutoff) \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error getting reminder subs: {e}")
        return []


def mark_reminder_sent(subscription_id: int) -> None:
    """Mark a subscription's reminder as sent."""
    client = get_client()
    if not client:
        return
    try:
        client.table("club_subscriptions") \
            .update({"reminder_sent": True}) \
            .eq("id", subscription_id) \
            .execute()
    except Exception as e:
        logger.error(f"Error marking reminder sent: {e}")


def get_expired_subscribers() -> List[Dict]:
    """Get active subscriptions past expiry + grace period."""
    client = get_client()
    if not client:
        return []
    try:
        grace_cutoff = (datetime.now() - timedelta(days=GRACE_DAYS)).isoformat()
        result = client.table("club_subscriptions") \
            .select("*") \
            .eq("status", "active") \
            .lte("expires_at", grace_cutoff) \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error getting expired subs: {e}")
        return []


def extend_subscription(user_id: int, days: int) -> bool:
    """Extend the expiration date of an active subscription."""
    client = get_client()
    if not client:
        return False
    try:
        sub = get_active_subscription(user_id)
        if not sub:
            return False
        
        current_expires = datetime.fromisoformat(sub['expires_at'])
        new_expires = current_expires + timedelta(days=days)
        
        client.table("club_subscriptions") \
            .update({"expires_at": new_expires.isoformat()}) \
            .eq("id", sub['id']) \
            .execute()
            
        logger.info(f"✅ Subscription extended by {days} days for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error extending subscription for {user_id}: {e}")
        return False


def mark_expired(user_id: int) -> None:
    """Mark all active subscriptions for a user as expired."""
    client = get_client()
    if not client:
        return
    try:
        client.table("club_subscriptions") \
            .update({"status": "expired"}) \
            .eq("user_id", user_id) \
            .eq("status", "active") \
            .execute()
        logger.info(f"🔴 Subscription expired for user {user_id}")
    except Exception as e:
        logger.error(f"Error marking expired: {e}")


def get_all_active_subscribers() -> List[Dict]:
    """Get all active subscriptions (for admin report)."""
    client = get_client()
    if not client:
        return []
    try:
        result = client.table("club_subscriptions") \
            .select("*") \
            .eq("status", "active") \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error getting active subs: {e}")
        return []


def get_active_subscriber_ids() -> Set[int]:
    """Get set of user IDs with active subscriptions."""
    subs = get_all_active_subscribers()
    return {s["user_id"] for s in subs}


# ============================================
# CAMPAIGN TARGETING
# ============================================

def get_non_subscriber_ids() -> Set[int]:
    """Get user IDs who are NOT active subscribers (for sales campaigns)."""
    client = get_client()
    if not client:
        return set()
    try:
        # Get all users
        all_users = client.table("club_users") \
            .select("id") \
            .neq("status", "blocked") \
            .execute()
        all_ids = {u["id"] for u in (all_users.data or [])}
        
        # Remove active subscribers
        subscriber_ids = get_active_subscriber_ids()
        
        return all_ids - subscriber_ids
    except Exception as e:
        logger.error(f"Error getting non-subscribers: {e}")
        return set()


def get_reminded_user_ids() -> Set[int]:
    """Get user IDs who opted into March reminder and are NOT subscribers."""
    client = get_client()
    if not client:
        return set()
    try:
        result = client.table("club_users") \
            .select("id") \
            .eq("remind_march", True) \
            .neq("status", "blocked") \
            .execute()
        reminded = {u["id"] for u in (result.data or [])}
        
        # Remove active subscribers
        subscriber_ids = get_active_subscriber_ids()
        
        return reminded - subscriber_ids
    except Exception as e:
        logger.error(f"Error getting reminded users: {e}")
        return set()


def get_subscribers_not_renewed(renewal_cutoff_date: str = "2026-03-01") -> Set[int]:
    """Get active subscriber IDs whose paid_at is before the cutoff (haven't renewed yet)."""
    client = get_client()
    if not client:
        return set()
    try:
        result = client.table("club_subscriptions") \
            .select("user_id") \
            .eq("status", "active") \
            .lt("paid_at", renewal_cutoff_date) \
            .execute()
        return {s["user_id"] for s in (result.data or [])}
    except Exception as e:
        logger.error(f"Error getting non-renewed subs: {e}")
        return set()


# ============================================
# CAMPAIGN STATE
# ============================================

def is_campaign_message_sent(campaign_id: str, message_id: str) -> bool:
    """Check if a specific campaign message was already sent."""
    client = get_client()
    if not client:
        return False
    try:
        result = client.table("club_campaign_state") \
            .select("campaign_id") \
            .eq("campaign_id", campaign_id) \
            .eq("message_id", message_id) \
            .maybe_single() \
            .execute()
        return result.data is not None
    except Exception as e:
        logger.error(f"Error checking campaign state: {e}")
        return False


def mark_campaign_message_sent(campaign_id: str, message_id: str, 
                                target_count: int = 0, success_count: int = 0) -> None:
    """Record that a campaign message was sent."""
    client = get_client()
    if not client:
        return
    try:
        client.table("club_campaign_state").upsert({
            "campaign_id": campaign_id,
            "message_id": message_id,
            "sent_at": datetime.now().isoformat(),
            "target_count": target_count,
            "success_count": success_count,
        }, on_conflict="campaign_id,message_id").execute()
    except Exception as e:
        logger.error(f"Error saving campaign state: {e}")


def get_sent_campaign_messages(campaign_id: str) -> Set[str]:
    """Get all sent message IDs for a campaign."""
    client = get_client()
    if not client:
        return set()
    try:
        result = client.table("club_campaign_state") \
            .select("message_id") \
            .eq("campaign_id", campaign_id) \
            .execute()
        return {r["message_id"] for r in (result.data or [])}
    except Exception as e:
        logger.error(f"Error getting campaign state: {e}")
        return set()


# ============================================
# WEBHOOK PARSER (unchanged from subscription_manager)
# ============================================

def parse_getcourse_webhook(data: dict) -> Optional[Dict]:
    """Parse GetCourse webhook payload. Returns {chat_id, email, name, status}."""
    try:
        utm_params = data.get("utm", {})
        tg_id = utm_params.get("tg_id") or data.get("tg_id")
        
        fields = data.get("fields", {})
        if not tg_id:
            tg_id = fields.get("telegram_id")
        
        email = data.get("email") or data.get("user", {}).get("email")
        name = data.get("name") or data.get("user", {}).get("name")
        status = data.get("status") or data.get("order_status")
        
        chat_id = int(tg_id) if tg_id else None
        
        # FALLBACK: If no tg_id, try matching by email
        if not chat_id and email:
            user = get_user_by_email(email)
            if user:
                chat_id = user["id"]
                logger.info(f"🔄 Matched payment to user {chat_id} by email: {email}")
        
        return {
            "chat_id": chat_id,
            "email": email,
            "name": name,
            "status": status
        }
    except Exception as e:
        logger.error(f"Error parsing webhook: {e}")
        return None


# ============================================
# REMINDER TEXT TEMPLATES
# ============================================

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
