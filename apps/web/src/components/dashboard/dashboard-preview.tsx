import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { JobMatchCard } from "@/components/jobs/job-match-card";
import { PathwayReportData } from "@/components/pathways/pathway-report";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { JobMatchRow } from "@/components/jobs/job-match-card";

export function DashboardTopMatches({
  matches,
  title,
  description,
  viewAllLabel,
}: {
  matches: JobMatchRow[];
  title: string;
  description: string;
  viewAllLabel: string;
}) {
  if (matches.length === 0) return null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <Button asChild variant="outline" size="sm" className="shrink-0">
          <Link href="/jobs">{viewAllLabel}</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {matches.map((row) => (
          <JobMatchCard key={row.match_id} row={row} />
        ))}
      </CardContent>
    </Card>
  );
}

export async function DashboardPathwayPreview({
  report,
}: {
  report: PathwayReportData | null;
}) {
  const t = await getTranslations("dashboard");

  if (!report) return null;

  // Lead with the score and the routes actually open to this candidate. Eligibility
  // badges without a score were the old preview's problem: they implied progress
  // toward an invitation that the numbers did not support.
  const eligibleRoutes = (report.gap_analysis ?? []).filter((g) => g.eligible).slice(0, 3);
  const moves = report.next_moves?.slice(0, 2) ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle className="text-base">{t("pathwayPreviewTitle")}</CardTitle>
          <CardDescription>{t("pathwayPreviewDescription")}</CardDescription>
        </div>
        <Button asChild variant="outline" size="sm" className="shrink-0">
          <Link href="/pathways">{t("viewPathwayReport")}</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {report.headline && (
          <div>
            <p className="text-3xl font-bold tabular-nums">{report.headline.crs}</p>
            <p className="text-sm text-muted-foreground">{report.headline.text}</p>
          </div>
        )}
        {eligibleRoutes.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {eligibleRoutes.map((g) => (
              <Badge key={g.id} variant={g.clears ? "default" : "outline"}>
                {g.route} {g.gap >= 0 ? `+${g.gap}` : g.gap}
              </Badge>
            ))}
          </div>
        )}
        {moves.length > 0 && (
          <ul className="space-y-2 text-sm text-muted-foreground">
            {moves.map((move) => (
              <li key={move.action} className="flex gap-2">
                <span className="text-primary">•</span>
                <span>
                  {move.action}{" "}
                  <span className="whitespace-nowrap text-foreground">(up to +{move.points})</span>
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="text-xs text-muted-foreground">{report.disclaimer}</p>
      </CardContent>
    </Card>
  );
}
