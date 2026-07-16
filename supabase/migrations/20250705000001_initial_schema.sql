-- CareerOS Phase 1: Core schema, RLS, PIPEDA export/delete RPCs
-- Region: deploy Supabase project in ca-central-1

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE public.immigration_status AS ENUM (
  'citizen',
  'pr',
  'pgwp',
  'closed_permit',
  'open_permit',
  'outside_canada'
);

CREATE TYPE public.language_proficiency AS ENUM (
  'none',
  'basic',
  'intermediate',
  'advanced',
  'native'
);

CREATE TYPE public.match_status AS ENUM (
  'new',
  'queued',
  'approved',
  'rejected',
  'expired'
);

CREATE TYPE public.application_status AS ENUM (
  'pending_review',
  'approved',
  'sent',
  'response',
  'interview',
  'offer',
  'rejected'
);

CREATE TYPE public.clearance_level AS ENUM (
  'none',
  'reliability',
  'secret'
);

CREATE TYPE public.remote_preference AS ENUM (
  'onsite',
  'hybrid',
  'remote',
  'any'
);

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  province TEXT,
  city TEXT,
  status public.immigration_status NOT NULL DEFAULT 'outside_canada',
  permit_expiry DATE,
  language_en public.language_proficiency NOT NULL DEFAULT 'intermediate',
  language_fr public.language_proficiency NOT NULL DEFAULT 'none',
  target_titles TEXT[] NOT NULL DEFAULT '{}',
  salary_min INTEGER,
  remote_pref public.remote_preference NOT NULL DEFAULT 'any',
  daily_send_cap INTEGER NOT NULL DEFAULT 10 CHECK (daily_send_cap BETWEEN 1 AND 50),
  locale TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'fr')),
  onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
  onboarding_step INTEGER NOT NULL DEFAULT 0 CHECK (onboarding_step BETWEEN 0 AND 5),
  match_score_threshold INTEGER NOT NULL DEFAULT 65 CHECK (match_score_threshold BETWEEN 0 AND 100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.profiles IS 'User profile: location, immigration status, job preferences, onboarding state';

-- ---------------------------------------------------------------------------
-- work_history
-- ---------------------------------------------------------------------------
CREATE TABLE public.work_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  employer TEXT,
  country TEXT NOT NULL DEFAULT 'CA',
  province TEXT,
  start_date DATE,
  end_date DATE,
  is_current BOOLEAN NOT NULL DEFAULT FALSE,
  duties_text TEXT,
  mapped_noc_code TEXT,
  mapped_teer SMALLINT CHECK (mapped_teer IS NULL OR mapped_teer BETWEEN 0 AND 5),
  noc_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
  months_canadian_experience INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX work_history_user_id_idx ON public.work_history(user_id);

-- ---------------------------------------------------------------------------
-- resumes
-- ---------------------------------------------------------------------------
CREATE TABLE public.resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  base_resume_json JSONB,
  storage_path TEXT,
  file_name TEXT,
  mime_type TEXT,
  is_primary BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX resumes_user_id_idx ON public.resumes(user_id);

-- ---------------------------------------------------------------------------
-- jobs (shared catalog — not user-scoped)
-- ---------------------------------------------------------------------------
CREATE TABLE public.jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  external_id TEXT,
  url TEXT NOT NULL,
  company TEXT,
  title TEXT NOT NULL,
  province TEXT,
  city TEXT,
  remote BOOLEAN NOT NULL DEFAULT FALSE,
  posted_at TIMESTAMPTZ,
  raw_jd TEXT,
  parsed_requirements JSONB NOT NULL DEFAULT '{}',
  noc_code TEXT,
  teer_level SMALLINT CHECK (teer_level IS NULL OR teer_level BETWEEN 0 AND 5),
  noc_confidence NUMERIC(4, 3) CHECK (noc_confidence IS NULL OR (noc_confidence >= 0 AND noc_confidence <= 1)),
  wage_offered NUMERIC(12, 2),
  wage_median_region NUMERIC(12, 2),
  wage_currency TEXT NOT NULL DEFAULT 'CAD',
  bilingual_required BOOLEAN NOT NULL DEFAULT FALSE,
  work_auth_required TEXT,
  lmia_flag BOOLEAN NOT NULL DEFAULT FALSE,
  clearance_required public.clearance_level NOT NULL DEFAULT 'none',
  dedupe_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX jobs_noc_code_idx ON public.jobs(noc_code);
CREATE INDEX jobs_province_idx ON public.jobs(province);
CREATE INDEX jobs_posted_at_idx ON public.jobs(posted_at DESC);
CREATE UNIQUE INDEX jobs_source_external_id_idx ON public.jobs(source, external_id)
  WHERE external_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- matches
-- ---------------------------------------------------------------------------
CREATE TABLE public.matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  match_score NUMERIC(5, 2) NOT NULL CHECK (match_score BETWEEN 0 AND 100),
  score_breakdown JSONB NOT NULL DEFAULT '{}',
  pathway_flags JSONB NOT NULL DEFAULT '{}',
  status public.match_status NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, job_id)
);

CREATE INDEX matches_user_id_status_idx ON public.matches(user_id, status);
CREATE INDEX matches_user_id_score_idx ON public.matches(user_id, match_score DESC);

-- ---------------------------------------------------------------------------
-- applications
-- ---------------------------------------------------------------------------
CREATE TABLE public.applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id UUID NOT NULL REFERENCES public.matches(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  tailored_resume_json JSONB,
  tailored_resume_pdf_path TEXT,
  cover_letter_text TEXT,
  submission_method TEXT,
  status public.application_status NOT NULL DEFAULT 'pending_review',
  sent_at TIMESTAMPTZ,
  response_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX applications_user_id_status_idx ON public.applications(user_id, status);

-- ---------------------------------------------------------------------------
-- pathway_reports
-- ---------------------------------------------------------------------------
CREATE TABLE public.pathway_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  report_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX pathway_reports_user_id_idx ON public.pathway_reports(user_id, generated_at DESC);

-- ---------------------------------------------------------------------------
-- activity_log (agent transparency)
-- ---------------------------------------------------------------------------
CREATE TABLE public.activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  entity_type TEXT,
  entity_id UUID,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX activity_log_user_id_created_idx ON public.activity_log(user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER work_history_updated_at
  BEFORE UPDATE ON public.work_history
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER resumes_updated_at
  BEFORE UPDATE ON public.resumes
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER jobs_updated_at
  BEFORE UPDATE ON public.jobs
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER matches_updated_at
  BEFORE UPDATE ON public.matches
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER applications_updated_at
  BEFORE UPDATE ON public.applications
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Auto-create profile on auth signup
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data ->> 'full_name', NEW.raw_user_meta_data ->> 'name', '')
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pathway_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;

-- profiles
CREATE POLICY "Users read own profile"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users update own profile"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- work_history
CREATE POLICY "Users manage own work history"
  ON public.work_history FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- resumes
CREATE POLICY "Users manage own resumes"
  ON public.resumes FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- jobs: authenticated users can read (shared catalog); writes via service role only
CREATE POLICY "Authenticated users read jobs"
  ON public.jobs FOR SELECT
  TO authenticated
  USING (true);

-- matches
CREATE POLICY "Users manage own matches"
  ON public.matches FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- applications
CREATE POLICY "Users manage own applications"
  ON public.applications FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- pathway_reports
CREATE POLICY "Users read own pathway reports"
  ON public.pathway_reports FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users insert own pathway reports"
  ON public.pathway_reports FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- activity_log
CREATE POLICY "Users read own activity log"
  ON public.activity_log FOR SELECT
  USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Storage bucket for resume PDFs (PIPEDA: user-scoped)
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'resumes',
  'resumes',
  false,
  10485760,
  ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Users upload own resumes"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

CREATE POLICY "Users read own resume files"
  ON storage.objects FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

CREATE POLICY "Users delete own resume files"
  ON storage.objects FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- ---------------------------------------------------------------------------
-- PIPEDA: data export RPC
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.data_export()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  uid UUID := auth.uid();
  result JSONB;
BEGIN
  IF uid IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  SELECT jsonb_build_object(
    'exported_at', now(),
    'profile', (SELECT to_jsonb(p.*) FROM public.profiles p WHERE p.id = uid),
    'work_history', COALESCE(
      (SELECT jsonb_agg(to_jsonb(wh.*) ORDER BY wh.sort_order)
       FROM public.work_history wh WHERE wh.user_id = uid),
      '[]'::jsonb
    ),
    'resumes', COALESCE(
      (SELECT jsonb_agg(to_jsonb(r.*) ORDER BY r.created_at DESC)
       FROM public.resumes r WHERE r.user_id = uid),
      '[]'::jsonb
    ),
    'matches', COALESCE(
      (SELECT jsonb_agg(
        jsonb_build_object(
          'match', to_jsonb(m.*),
          'job', (SELECT to_jsonb(j.*) FROM public.jobs j WHERE j.id = m.job_id)
        )
       ORDER BY m.match_score DESC)
       FROM public.matches m WHERE m.user_id = uid),
      '[]'::jsonb
    ),
    'applications', COALESCE(
      (SELECT jsonb_agg(to_jsonb(a.*) ORDER BY a.created_at DESC)
       FROM public.applications a WHERE a.user_id = uid),
      '[]'::jsonb
    ),
    'pathway_reports', COALESCE(
      (SELECT jsonb_agg(to_jsonb(pr.*) ORDER BY pr.generated_at DESC)
       FROM public.pathway_reports pr WHERE pr.user_id = uid),
      '[]'::jsonb
    ),
    'activity_log', COALESCE(
      (SELECT jsonb_agg(to_jsonb(al.*) ORDER BY al.created_at DESC)
       FROM public.activity_log al WHERE al.user_id = uid),
      '[]'::jsonb
    )
  ) INTO result;

  RETURN result;
END;
$$;

GRANT EXECUTE ON FUNCTION public.data_export() TO authenticated;

-- ---------------------------------------------------------------------------
-- PIPEDA: account deletion (cascade via FK + storage cleanup)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.delete_user_account()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, storage
AS $$
DECLARE
  uid UUID := auth.uid();
BEGIN
  IF uid IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  DELETE FROM storage.objects
  WHERE bucket_id = 'resumes'
    AND (storage.foldername(name))[1] = uid::text;

  DELETE FROM auth.users WHERE id = uid;
END;
$$;

GRANT EXECUTE ON FUNCTION public.delete_user_account() TO authenticated;
