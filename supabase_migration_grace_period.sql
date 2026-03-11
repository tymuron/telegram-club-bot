-- ============================================
-- Migration: Add grace_period support and warned_at
-- Run this AFTER supabase_migration.sql if you already have the base schema
-- Safe to run multiple times (uses IF NOT EXISTS / IF EXISTS)
-- ============================================

-- Add warned_at for two-phase kick (warn 24h before actually kicking)
ALTER TABLE club_subscriptions
  ADD COLUMN IF NOT EXISTS warned_at TIMESTAMPTZ;

-- status column is TEXT, so 'grace_period' works without enum change
-- No change needed for grace_period

COMMENT ON COLUMN club_subscriptions.warned_at IS 'When user was warned about expiry (Phase 1 of kick)';
COMMENT ON COLUMN club_subscriptions.status IS 'active | grace_period | expired';
