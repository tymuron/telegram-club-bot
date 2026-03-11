# GetCourse Webhook Setup

For payments to appear in Supabase and users to receive invite links, configure GetCourse to call this bot when an order is paid.

## 1. Webhook URL (IMPORTANT)

**Use this URL:**
```
https://telegram-club-bot-z7xk.onrender.com/webhook/payment
```

Do **NOT** use `/webhook/{BOT_TOKEN}` — that path is deprecated and leaks your token.

## 2. GetCourse Process

1. Go to **Процессы** (Processes) → create or edit a process **по заказам** (for orders).
2. Add trigger: e.g. "Заказ оплачен" / "Order paid".
3. Add operation **"Вызвать URL"** (Call URL).
4. Set **Method: POST**, Body: **x-www-form-urlencoded**.

## 3. Variable syntax — use single braces `{}`

GetCourse uses **single curly braces** `{variable}`. Double braces `{{variable}}` are NOT substituted and will be sent literally.

### Best setup: token-based matching

The bot now adds a `token=...` parameter to every payment link it generates.
This is the most reliable way to map a paid GetCourse order back to the exact
Telegram user.

### For POST body (Тело запроса), add these parameters:

| Key   | Value (copy exactly)        |
|-------|-----------------------------|
| token | `{create_session.token}`    |
| email | `{object.user.email}`       |
| name  | `{object.user.first_name}`  |
| status| `completed` (or `{object.status}`) |

**For Orders process**, the object is the order; use `object.user.email` for the buyer's email. Do **not** use `{user.email}` or `{{user.email}}`.

### Fallback

If `create_session.token` is empty, the bot falls back to **email matching**.
So the user should still write `/start` and give the same email before paying.

## 4. Status values

The bot treats as **paid**: `completed`, `paid`, `оплачен`, `завершен`, `success`.

## 5. Test

After a payment, check Render logs. You should see:
```
📥 GetCourse webhook received: {'email': 'real@email.com', 'name': 'Anna', 'status': 'completed', ...}
💰 Parsed: tg_id=..., status=completed, email=...
```

If you see `{{variable}}` in the log, the variable was not substituted — fix the braces in GetCourse.
