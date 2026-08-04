-- Lock down grant_report_credit.
--
-- Postgres grants EXECUTE on new functions to PUBLIC by default, and Supabase
-- exposes every public-schema function as a PostgREST RPC endpoint. Combined with
-- SECURITY DEFINER, that made /rest/v1/rpc/grant_report_credit callable by anon —
-- anyone could mint themselves unlimited report credits without paying.
--
-- Only the Stripe webhook may call this, and it uses the service role.

REVOKE ALL ON FUNCTION public.grant_report_credit(uuid, text, text, integer, text)
  FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.grant_report_credit(uuid, text, text, integer, text)
  TO service_role;
