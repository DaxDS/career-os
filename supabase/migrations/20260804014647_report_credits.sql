-- One-time PR pathway report purchases.
--
-- The Pro subscription and a single paid report are different products. Without a
-- separate credit ledger the Stripe webhook cannot tell them apart, and a one-time
-- payment would be indistinguishable from a subscription start.

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS report_credits INTEGER NOT NULL DEFAULT 0
    CHECK (report_credits >= 0);

CREATE TABLE IF NOT EXISTS report_purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  stripe_session_id TEXT NOT NULL,
  stripe_payment_intent TEXT,
  amount_total INTEGER,
  currency TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Stripe retries webhooks; the unique constraint makes replay a no-op rather than
  -- granting a second credit for the same payment.
  CONSTRAINT report_purchases_session_unique UNIQUE (stripe_session_id)
);

CREATE INDEX IF NOT EXISTS report_purchases_user_id_idx ON report_purchases (user_id);

ALTER TABLE report_purchases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users read own report purchases" ON report_purchases;
CREATE POLICY "Users read own report purchases" ON report_purchases
  FOR SELECT USING (auth.uid() = user_id);

-- Writes come only from the service role in the Stripe webhook. No insert/update
-- policy is defined for end users on purpose.

CREATE OR REPLACE FUNCTION grant_report_credit(
  p_user_id UUID,
  p_session_id TEXT,
  p_payment_intent TEXT DEFAULT NULL,
  p_amount_total INTEGER DEFAULT NULL,
  p_currency TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  -- GET DIAGNOSTICS returns an integer. Assigning it straight to a BOOLEAN fails,
  -- because int -> bool is an explicit-only cast and PL/pgSQL assignment does not
  -- apply explicit casts.
  rows_inserted INTEGER := 0;
BEGIN
  INSERT INTO report_purchases (
    user_id, stripe_session_id, stripe_payment_intent, amount_total, currency
  )
  VALUES (p_user_id, p_session_id, p_payment_intent, p_amount_total, p_currency)
  ON CONFLICT (stripe_session_id) DO NOTHING;

  GET DIAGNOSTICS rows_inserted = ROW_COUNT;

  IF rows_inserted > 0 THEN
    UPDATE profiles SET report_credits = report_credits + 1 WHERE id = p_user_id;
  END IF;

  RETURN rows_inserted > 0;
END;
$$;
