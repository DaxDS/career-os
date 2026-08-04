-- CRS inputs on profiles.
--
-- The product's core promise is a real Comprehensive Ranking System score, but the
-- profile carried none of the inputs the grid needs: no age, no credential level, no
-- per-ability language scores. Every score would have come out near zero.
--
-- Language is stored per ability as CLB/NCLC integers rather than the coarse
-- language_proficiency enum, because the grid scores each of the four abilities
-- separately and a candidate is routinely CLB 9 in reading and CLB 7 in speaking.
-- The existing language_en / language_fr enums are left in place for the job-matching
-- code that already reads them.

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS date_of_birth DATE,
  ADD COLUMN IF NOT EXISTS education_level TEXT,
  ADD COLUMN IF NOT EXISTS clb_en_reading   SMALLINT CHECK (clb_en_reading   BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS clb_en_writing   SMALLINT CHECK (clb_en_writing   BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS clb_en_listening SMALLINT CHECK (clb_en_listening BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS clb_en_speaking  SMALLINT CHECK (clb_en_speaking  BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS nclc_fr_reading   SMALLINT CHECK (nclc_fr_reading   BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS nclc_fr_writing   SMALLINT CHECK (nclc_fr_writing   BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS nclc_fr_listening SMALLINT CHECK (nclc_fr_listening BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS nclc_fr_speaking  SMALLINT CHECK (nclc_fr_speaking  BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS has_accompanying_spouse BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS spouse_education_level TEXT,
  ADD COLUMN IF NOT EXISTS spouse_clb_reading   SMALLINT CHECK (spouse_clb_reading   BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS spouse_clb_writing   SMALLINT CHECK (spouse_clb_writing   BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS spouse_clb_listening SMALLINT CHECK (spouse_clb_listening BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS spouse_clb_speaking  SMALLINT CHECK (spouse_clb_speaking  BETWEEN 0 AND 12),
  ADD COLUMN IF NOT EXISTS spouse_canadian_experience_years SMALLINT
    CHECK (spouse_canadian_experience_years BETWEEN 0 AND 50),
  ADD COLUMN IF NOT EXISTS foreign_experience_months INTEGER
    CHECK (foreign_experience_months >= 0),
  ADD COLUMN IF NOT EXISTS has_provincial_nomination BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS sibling_in_canada BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS canadian_study_credential TEXT,
  ADD COLUMN IF NOT EXISTS trades_certificate BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS crs_profile_completed BOOLEAN NOT NULL DEFAULT FALSE;

-- Credential levels mirror the CRS education table exactly, so the grid can index
-- them directly rather than mapping through a lossy intermediate vocabulary.
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_education_level_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_education_level_check
  CHECK (education_level IS NULL OR education_level IN (
    'none',
    'secondary',
    'one_year_post_secondary',
    'two_year_post_secondary',
    'bachelors_or_three_year',
    'two_or_more_credentials',
    'masters_or_professional',
    'doctoral'
  ));

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_spouse_education_level_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_spouse_education_level_check
  CHECK (spouse_education_level IS NULL OR spouse_education_level IN (
    'none',
    'secondary',
    'one_year_post_secondary',
    'two_year_post_secondary',
    'bachelors_or_three_year',
    'two_or_more_credentials',
    'masters_or_professional',
    'doctoral'
  ));

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_canadian_study_credential_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_canadian_study_credential_check
  CHECK (canadian_study_credential IS NULL OR canadian_study_credential IN (
    'one_or_two_year',
    'three_year_plus'
  ));
