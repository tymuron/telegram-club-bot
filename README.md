# Telegram Bot for Paid Club Access

This bot greets users, sends an invoice for membership, and automatically grants a single-use invite link upon successful payment.

## Setup Guide

### 1. Create the Bot
1. Open Telegram and search for **@BotFather**.
2. Send `/newbot`.
3. Follow the instructions to name your bot and get the **username**.
4. **Copy the HTTP API Token**.
5. Paste this token into your `.env` file as `BOT_TOKEN`.

### 2. Configure Payments
1. In **@BotFather**, send `/mybots`.
2. Select your bot.
3. Select **Bot Settings** -> **Payments**.
4. Choose a provider (e.g., **Stripe**).
5. Select **Stripe Test** (for testing) or **Connect Stripe** (for live).
6. Follow the flow to connect your account.
7. **Copy the Payment Token** (it looks like `284685063:TEST:...`).
8. Paste this into your `.env` file as `PAYMENT_PROVIDER_TOKEN`.

### 3. Setup the Private Club (Channel/Group)
1. Create a **New Channel** or **Group** in Telegram.
2. Go to **Manage Channel** -> **Administrators**.
3. **Add your bot** as an Administrator.
4. Ensure the bot has **"Invite Users via Link"** permission.
5. Determine the **Channel ID**:
   - Forward a message from the channel to **@JsonDumpBot** or use a similar tool to find the ID (usually starts with `-100`).
   - Or, just try running the bot and make it print the chat ID if unsure (or easier: make the channel public temporarily, get username, then make private).
   - Paste the ID into `.env` as `CHANNEL_ID`.

### 4. Install & Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your real tokens!
   ```
3. Run the bot:
   ```bash
   python bot.py
   ```

## Usage
- User sends `/start` -> Bot greets.
- User sends `/buy` -> Bot sends invoice.
- User pays -> Bot verifies payload and payment.
- Bot sends **Invite Link**.
