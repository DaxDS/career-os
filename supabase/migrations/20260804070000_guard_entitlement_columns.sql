-- Extend the billing guard to every column that grants paid access.
--
-- The guard covered plan and the stripe_* fields but not report_credits or
-- daily_send_cap. RLS lets a user update their own profiles row, so a signed-in user
-- could PATCH /rest/v1/profiles with {"report_credits": 999} and take unlimited paid
-- reports without paying. Verified exploitable before this change, and verified
-- blocked after — while normal profile edits and the service-role webhook still work.
--
-- Also pins search_path, which the linter flagged as mutable.

CREATE OR REPLACE FUNCTION public.guard_profile_billing_columns()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $function$
DECLARE
  is_privileged BOOLEAN := current_setting('role', true) IN ('service_role', 'postgres', 'supabase_admin')
                           OR current_user IN ('postgres', 'supabase_admin', 'service_role');
BEGIN
  IF (
    NEW.plan IS DISTINCT FROM OLD.plan
    OR NEW.stripe_customer_id IS DISTINCT FROM OLD.stripe_customer_id
    OR NEW.stripe_subscription_id IS DISTINCT FROM OLD.stripe_subscription_id
    OR NEW.plan_status IS DISTINCT FROM OLD.plan_status
    OR NEW.plan_renews_at IS DISTINCT FROM OLD.plan_renews_at
    -- Entitlement columns: granted only by the Stripe webhook, never by the user.
    OR NEW.report_credits IS DISTINCT FROM OLD.report_credits
    OR NEW.daily_send_cap IS DISTINCT FROM OLD.daily_send_cap
  ) THEN
    IF is_privileged THEN
      RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Billing and entitlement fields are managed by Stripe and cannot be changed directly';
  END IF;
  RETURN NEW;
END;
$function$;
