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

  const flags = report.pathway_flags;
  const recs = report.recommendations?.slice(0, 2) ?? [];

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
        <div className="flex flex-wrap gap-2">
          {flags?.ee_eligible && <Badge variant="secondary">Express Entry eligible</Badge>}
          {flags?.aip_relevant && <Badge variant="secondary">AIP relevant</Badge>}
          {flags?.ee_categories?.map((c) => (
            <Badge key={c} variant="outline">
              EE {c}
            </Badge>
          ))}
          {flags?.pnp_streams?.slice(0, 2).map((s) => (
            <Badge key={s} variant="outline">
              PNP {s.replace(/_/g, " ")}
            </Badge>
          ))}
        </div>
        {recs.length > 0 && (
          <ul className="space-y-2 text-sm text-muted-foreground">
            {recs.map((rec) => (
              <li key={rec} className="flex gap-2">
                <span className="text-primary">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="text-xs text-muted-foreground">{report.disclaimer}</p>
      </CardContent>
    </Card>
  );
}
