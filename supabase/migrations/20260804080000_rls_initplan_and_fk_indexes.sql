-- Wrap auth.uid() in a scalar subquery so Postgres evaluates it once per statement
-- instead of once per row. Semantics identical; verified cross-user isolation still
-- holds after the change (own rows visible, other users' rows invisible and
-- unmodifiable). Plus covering indexes for two foreign keys.
ALTER POLICY "Users read own profile" ON public.profiles USING ((select auth.uid()) = id);
ALTER POLICY "Users update own profile" ON public.profiles
  USING ((select auth.uid()) = id) WITH CHECK ((select auth.uid()) = id);
ALTER POLICY "Users manage own work history" ON public.work_history
  USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);
ALTER POLICY "Users manage own resumes" ON public.resumes
  USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);
ALTER POLICY "Users manage own matches" ON public.matches
  USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);
ALTER POLICY "Users manage own applications" ON public.applications
  USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);
ALTER POLICY "Users read own pathway reports" ON public.pathway_reports
  USING ((select auth.uid()) = user_id);
ALTER POLICY "Users insert own pathway reports" ON public.pathway_reports
  WITH CHECK ((select auth.uid()) = user_id);
ALTER POLICY "Users read own activity log" ON public.activity_log
  USING ((select auth.uid()) = user_id);
ALTER POLICY "Users read own report purchases" ON public.report_purchases
  USING ((select auth.uid()) = user_id);

CREATE INDEX IF NOT EXISTS applications_match_id_idx ON public.applications (match_id);
CREATE INDEX IF NOT EXISTS matches_job_id_idx ON public.matches (job_id);
