-- Billing: plan column, Stripe fields, RLS guard on billing writes
-- Free: 5 sends/day, 10 tailored apps/month | Pro: 25 sends/day, unlimited tailoring

-- Migrate from Phase 4 plan_tier if present
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS plan_status TEXT,
  ADD COLUMN IF NOT EXISTS plan_renews_at TIMESTAMPTZ;

-- Backfill plan from legacy plan_tier enum column (may exist from 20250705000002)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'plan_tier'
  ) THEN
    EXECUTE $sql$
      UPDATE public.profiles
      SET plan = plan_tier::text
      WHERE plan = 'free' AND plan_tier IS NOT NULL
    $sql$;
  END IF;
END $$;

-- Backfill plan_status from legacy subscription_status
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'subscription_status'
  ) THEN
    EXECUTE $sql$
      UPDATE public.profiles
      SET plan_status = subscription_status
      WHERE plan_status IS NULL AND subscription_status IS NOT NULL
    $sql$;
  END IF;
END $$;

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_plan_check;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_plan_check CHECK (plan IN ('free', 'pro'));

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_plan_status_check;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_plan_status_check
  CHECK (plan_status IS NULL OR plan_status IN ('active', 'past_due', 'canceled'));

COMMENT ON COLUMN public.profiles.plan IS 'Subscription tier: free or pro (Stripe webhook only)';
COMMENT ON COLUMN public.profiles.plan_status IS 'Stripe subscription status mirror';
COMMENT ON COLUMN public.profiles.plan_renews_at IS 'Next billing period end from Stripe';
COMMENT ON COLUMN public.profiles.stripe_customer_id IS 'Stripe customer id — webhook writes only';
COMMENT ON COLUMN public.profiles.stripe_subscription_id IS 'Stripe subscription id — webhook writes only';

-- Ensure stripe columns exist (idempotent with 20250705000002)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT;

-- Drop legacy columns after migration
ALTER TABLE public.profiles DROP COLUMN IF EXISTS plan_tier;
ALTER TABLE public.profiles DROP COLUMN IF EXISTS subscription_status;

DROP TYPE IF EXISTS public.plan_tier;

-- Prevent authenticated users from self-upgrading via profile UPDATE
CREATE OR REPLACE FUNCTION public.guard_profile_billing_columns()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF (
    NEW.plan IS DISTINCT FROM OLD.plan
    OR NEW.stripe_customer_id IS DISTINCT FROM OLD.stripe_customer_id
    OR NEW.stripe_subscription_id IS DISTINCT FROM OLD.stripe_subscription_id
    OR NEW.plan_status IS DISTINCT FROM OLD.plan_status
    OR NEW.plan_renews_at IS DISTINCT FROM OLD.plan_renews_at
  ) THEN
    IF current_setting('role', true) = 'service_role' THEN
      RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Billing fields are managed by Stripe and cannot be changed directly';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS guard_profile_billing ON public.profiles;
CREATE TRIGGER guard_profile_billing
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.guard_profile_billing_columns();

-- Users read own profile (includes billing columns) — existing SELECT policy covers this.
-- Billing writes: service role only (bypasses RLS) via webhook handler.
