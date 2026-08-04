-- Canadian skilled work experience, entered directly.
--
-- It was only ever derived from work_history dates. A user whose history lacked dates
-- scored zero with no field anywhere asking about it — the single largest silent
-- undercount in the grid, worth up to 80 core points plus transferability.
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS canadian_experience_months INTEGER
    CHECK (canadian_experience_months IS NULL OR canadian_experience_months >= 0);
