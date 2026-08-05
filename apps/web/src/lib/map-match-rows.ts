import type { JobMatchRow } from "@/components/jobs/job-match-card";
import type { PathwayFlags, PrDeltaFlags, ScoreBreakdown } from "@careeros/shared";

type RawMatchRow = {
  id: string;
  match_score: number;
  score_breakdown: unknown;
  pathway_flags: unknown;
  status: string;
  jobs: JobMatchRow["job"] | JobMatchRow["job"][] | null;
};

export function mapMatchRows(rows: RawMatchRow[] | null | undefined): JobMatchRow[] {
  return (rows || [])
    .filter((m) => m.jobs && !Array.isArray(m.jobs))
    .map((m) => ({
      match_id: m.id,
      match_score: Number(m.match_score),
      score_breakdown: (m.score_breakdown || {}) as ScoreBreakdown,
      pathway_flags: (m.pathway_flags || {}) as PathwayFlags & PrDeltaFlags,
      status: m.status,
      job: m.jobs as JobMatchRow["job"],
    }));
}

export const MATCH_SELECT = `
  id,
  match_score,
  score_breakdown,
  pathway_flags,
  status,
  jobs (
    id,
    title,
    company,
    city,
    province,
    url,
    noc_code,
    teer_level,
    noc_confidence,
    wage_offered,
    wage_median_region,
    bilingual_required,
    source
  )
` as const;
