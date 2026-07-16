"use client";

import { useTranslations } from "next-intl";
import { JobMatchBadges } from "@/components/jobs/job-match-badges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const DEMO_JOB = {
  title: "Software Developer",
  company: "Example employer",
  location: "Halifax, NS",
  matchScore: 78,
  job: {
    noc_code: "21232",
    teer_level: 1,
    noc_confidence: 0.92,
    wage_offered: 48,
    wage_median_region: 40,
    bilingual_required: false,
    source: "job_bank",
  },
  pathway_flags: {
    ee_eligible: true,
    ee_categories: ["STEM"],
    pnp_streams: ["ns_in_demand"],
    aip_relevant: false,
  },
};

export function LandingJobExample() {
  const t = useTranslations("landing.jobExample");
  const td = useTranslations("disclaimer");

  return (
    <Card className="mx-auto max-w-xl text-left shadow-md">
      <CardHeader className="pb-3">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("label")}
        </p>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <CardTitle className="text-lg">{DEMO_JOB.title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {DEMO_JOB.company} · {DEMO_JOB.location}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-2xl font-bold text-primary">{DEMO_JOB.matchScore}</p>
            <p className="text-xs text-muted-foreground">{t("matchScore")}</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <JobMatchBadges job={DEMO_JOB.job} pathway_flags={DEMO_JOB.pathway_flags} />
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{td("pathway")}</p>
      </CardContent>
    </Card>
  );
}
