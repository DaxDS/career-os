-- Phase 4: Billing, waitlist, usage tracking

CREATE TYPE public.plan_tier AS ENUM ('free', 'pro');

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS plan_tier public.plan_tier NOT NULL DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
  ADD COLUMN IF NOT EXISTS subscription_status TEXT;

COMMENT ON COLUMN public.profiles.plan_tier IS 'free or pro — set by Stripe webhook';

-- Marketing waitlist (PIPEDA: email only, optional name)
CREATE TABLE IF NOT EXISTS public.waitlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  source TEXT NOT NULL DEFAULT 'landing',
  locale TEXT DEFAULT 'en',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;

-- Anyone can join waitlist (insert only, no read)
CREATE POLICY "Anyone can join waitlist"
  ON public.waitlist FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- Service role reads waitlist for exports; no public SELECT

CREATE INDEX IF NOT EXISTS activity_log_user_action_idx
  ON public.activity_log(user_id, action, created_at DESC);
