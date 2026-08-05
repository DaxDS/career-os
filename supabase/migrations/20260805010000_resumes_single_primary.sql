-- Enforce at most one primary resume per user.
--
-- Live data already violated this: one account had two rows both is_primary=true for
-- the same re-uploaded file, because the upload step always inserted with
-- is_primary=true and never unset the previous one. loadBaseResume() selects
-- is_primary=true with no ORDER BY, so which row wins is undefined. Currently inert
-- only because base_resume_json is never populated by anything yet — the moment a
-- parser writes to it, this becomes a real correctness bug, not just clutter.

DELETE FROM resumes a
USING resumes b
WHERE a.user_id = b.user_id
  AND a.is_primary = true
  AND b.is_primary = true
  AND a.created_at < b.created_at;

CREATE UNIQUE INDEX IF NOT EXISTS resumes_one_primary_per_user
  ON resumes (user_id) WHERE is_primary = true;

-- Old-format Word documents (.doc) were accepted by the client's file picker and
-- validation list, then rejected by the bucket's allowed_mime_types, which only ever
-- listed pdf/docx/txt. The client promised a capability the server did not have.
UPDATE storage.buckets
SET allowed_mime_types = array_append(allowed_mime_types, 'application/msword')
WHERE id = 'resumes' AND NOT ('application/msword' = ANY(allowed_mime_types));
