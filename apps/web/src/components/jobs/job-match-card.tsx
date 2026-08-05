import type { PathwayFlags, PrDeltaFlags, ScoreBreakdown } from "@careeros/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JobMatchBadges } from "@/components/jobs/job-match-badges";
import { PrepareApplicationButton } from "@/components/jobs/prepare-button";

export interface JobMatchRow {
  match_id: string;
  match_score: number;
  score_breakdown: ScoreBreakdown;
  pathway_flags: PathwayFlags & PrDeltaFlags;
  status: string;
  job: {
    id: string;
    title: string;
    company: string | null;
    city: string | null;
    province: string | null;
    url: string;
    noc_code: string | null;
    teer_level: number | null;
    noc_confidence: number | null;
    wage_offered: number | null;
    wage_median_region: number | null;
    bilingual_required: boolean;
    source: string;
  };
}

export function JobMatchCard({ row }: { row: JobMatchRow }) {
  const gaps = row.score_breakdown.gaps || [];
  // score.ts writes a single explanatory sentence rather than a gaps list — this was
  // being computed and stored on every real match, then never rendered anywhere.
  const verdict = row.score_breakdown.verdict;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-lg">
              <a href={row.job.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                {row.job.title}
              </a>
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {row.job.company}
              {(row.job.city || row.job.province) && (
                <> · {[row.job.city, row.job.province].filter(Boolean).join(", ")}</>
              )}
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-primary">{Math.round(row.match_score)}</p>
            <p className="text-xs text-muted-foreground">match score</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <JobMatchBadges job={row.job} pathway_flags={row.pathway_flags} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {verdict && (
          <div className="rounded-md bg-muted/50 p-3 text-sm">
            <p className="mb-1 font-medium">What this role does for your PR odds</p>
            <p className="text-muted-foreground">{verdict}</p>
          </div>
        )}
        {gaps.length > 0 && (
          <div className="rounded-md bg-muted/50 p-3 text-sm">
            <p className="mb-1 font-medium">Gap analysis</p>
            <ul className="list-inside list-disc space-y-1 text-muted-foreground">
              {gaps.map((gap, i) => (
                <li key={i}>{gap}</li>
              ))}
            </ul>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          This is informational only, based on published program criteria, and is not immigration advice.
        </p>
        <PrepareApplicationButton matchId={row.match_id} status={row.status} />
      </CardContent>
    </Card>
  );
}
