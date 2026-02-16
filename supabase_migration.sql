-- ============================================
-- Vastu Club Bot — Supabase Migration
-- Run this in Supabase SQL Editor (Dashboard → SQL)
-- ============================================

-- Users table (leads who started the bot)
CREATE TABLE IF NOT EXISTS club_users (
  id BIGINT PRIMARY KEY,                      -- Telegram user ID
  first_name TEXT,
  last_name TEXT,
  username TEXT,
  email TEXT,
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  remind_march BOOLEAN DEFAULT FALSE,
  remind_opted_at TIMESTAMPTZ,
  status TEXT DEFAULT 'lead',                 -- lead, blocked
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions table (payment records)
CREATE TABLE IF NOT EXISTS club_subscriptions (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES club_users(id) ON DELETE CASCADE,
  paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'active',               -- active, expired
  reminder_sent BOOLEAN DEFAULT FALSE,
  payment_source TEXT DEFAULT 'getcourse',    -- getcourse, manual, telegram_pay
  renewed_count INT DEFAULT 1,
  email TEXT,
  name TEXT
);

-- Campaign state (tracks which messages were sent)
CREATE TABLE IF NOT EXISTS club_campaign_state (
  campaign_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  target_count INT DEFAULT 0,
  success_count INT DEFAULT 0,
  PRIMARY KEY (campaign_id, message_id)
);

-- Index for fast subscription lookups
CREATE INDEX IF NOT EXISTS idx_club_subs_user_status 
  ON club_subscriptions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_club_subs_expires 
  ON club_subscriptions(expires_at) 
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_club_users_remind 
  ON club_users(remind_march) 
  WHERE remind_march = TRUE;

-- Enable Row Level Security (recommended by Supabase but we use service key)
ALTER TABLE club_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE club_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE club_campaign_state ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role access" ON club_users FOR ALL 
  USING (true) WITH CHECK (true);
CREATE POLICY "Service role access" ON club_subscriptions FOR ALL 
  USING (true) WITH CHECK (true);
CREATE POLICY "Service role access" ON club_campaign_state FOR ALL 
  USING (true) WITH CHECK (true);
