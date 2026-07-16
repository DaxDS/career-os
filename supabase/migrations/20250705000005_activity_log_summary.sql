-- Standardize activity_log: plain-language summary column for timeline UI

ALTER TABLE public.activity_log
  ADD COLUMN IF NOT EXISTS summary TEXT;

COMMENT ON COLUMN public.activity_log.summary IS 'Human-readable description shown in the activity timeline';
COMMENT ON COLUMN public.activity_log.action IS 'Machine key, e.g. discovery_completed, dispatch_blocked';
