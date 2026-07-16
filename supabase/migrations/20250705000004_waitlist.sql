-- Waitlist: public email capture on marketing landing page
-- Schema: email (unique), optional province, source tag, created_at

CREATE TABLE IF NOT EXISTS public.waitlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  province TEXT,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Align legacy Phase 4 waitlist columns if present
ALTER TABLE public.waitlist DROP COLUMN IF EXISTS name;
ALTER TABLE public.waitlist DROP COLUMN IF EXISTS locale;
ALTER TABLE public.waitlist ADD COLUMN IF NOT EXISTS province TEXT;

ALTER TABLE public.waitlist ALTER COLUMN source DROP NOT NULL;
ALTER TABLE public.waitlist ALTER COLUMN source DROP DEFAULT;

ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can join waitlist" ON public.waitlist;
DROP POLICY IF EXISTS "waitlist_public_insert" ON public.waitlist;

-- Public form: anonymous (and signed-in visitors) may INSERT only
CREATE POLICY "waitlist_public_insert"
  ON public.waitlist FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- No SELECT / UPDATE / DELETE policies for anon or authenticated (denied by default).
-- Service role bypasses RLS for admin reads and exports.
