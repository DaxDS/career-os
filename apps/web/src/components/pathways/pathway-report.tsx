"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface GapRow {
  route: string;
  id: string;
  typical_cutoff: number;
  your_score: number;
  gap: number;
  score_clears_cutoff: boolean;
  eligible: boolean;
  eligibility_reason: string;
  clears: boolean;
  itas_last_12_months: number;
  last_drawn: string | null;
}

export interface NextMove {
  action: string;
  points: number;
  effort: string;
  detail: string;
}

export interface PathwayReportData {
  generated_at?: string;
  disclaimer?: string;
  headline?: { crs: number; status: string; text: string };
  crs?: {
    total: number;
    core: number;
    spouse: number;
    transferability: number;
    additional: number;
    breakdown: Record<string, number>;
    grid_version?: string;
  };
  profile_summary?: {
    status?: string;
    province?: string;
    permit_expiry?: string;
    canadian_experience_months?: number;
    foreign_experience_months?: number;
    primary_noc?: string;
    primary_teer?: number;
  };
  draw_landscape?: {
    live?: Array<{ id: string; label: string; rounds_last_12_months: number }>;
    dormant?: Array<{ id: string; label: string; warning?: string }>;
  };
  gap_analysis?: GapRow[];
  next_moves?: NextMove[];
  permit_runway_days?: number;
  arranged_employment_note?: string;
  draws_metadata?: { last_verified?: string; source_url?: string };
}

const BREAKDOWN_LABELS: Record<string, string> = {
  age: "Age",
  education: "Education",
  first_language: "First official language",
  second_language: "Second official language",
  canadian_experience: "Canadian work experience",
  spouse_education: "Spouse education",
  spouse_language: "Spouse language",
  spouse_canadian_experience: "Spouse Canadian experience",
  education_transferability: "Skill transferability — education",
  foreign_experience_transferability: "Skill transferability — foreign experience",
  trades_transferability: "Skill transferability — trades certificate",
  provincial_nomination: "Provincial nomination",
  french_bonus: "French proficiency bonus",
  canadian_study: "Canadian study credential",
  sibling_in_canada: "Sibling in Canada",
  arranged_employment: "Arranged employment (removed by IRCC)",
};

export function PathwayReportView({ report }: { report: PathwayReportData | null }) {
  const router = useRouter();
  const tb = useTranslations("billing");
  const tp = useTranslations("pathways");
  const [loading, setLoading] = useState(false);

  async function regenerate() {
    setLoading(true);
    try {
      const res = await fetch("/api/pathways/generate", { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 402) {
          throw new Error(`${data.error || tp("proFeature")} — ${tb("upgradeAtSettings")}`);
        }
        throw new Error(data.error || "Failed");
      }
      router.refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  if (!report) {
    return (
      <div className="space-y-4 rounded-xl border border-dashed p-12 text-center">
        <p className="text-muted-foreground">No pathway report yet.</p>
        <Button onClick={regenerate} disabled={loading}>
          {loading ? "Generating…" : "Generate report"}
        </Button>
      </div>
    );
  }

  const crs = report.crs;
  const summary = report.profile_summary;
  const eligible = (report.gap_analysis || []).filter((g) => g.eligible);
  const ineligible = (report.gap_analysis || []).filter((g) => !g.eligible);
  const dormant = report.draw_landscape?.dormant || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          Generated {report.generated_at ? new Date(report.generated_at).toLocaleString() : "—"}
        </p>
        <Button variant="outline" size="sm" onClick={regenerate} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh report"}
        </Button>
      </div>

      {report.headline && (
        <Card className="border-primary/40 bg-primary/5">
          <CardContent className="p-6">
            <p className="text-4xl font-bold tabular-nums">{report.headline.crs}</p>
            <p className="text-sm uppercase tracking-wide text-muted-foreground">
              Your CRS score
            </p>
            <p className="mt-3 text-base">{report.headline.text}</p>
          </CardContent>
        </Card>
      )}

      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
        {report.disclaimer}
      </div>

      {eligible.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Routes you qualify for</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {eligible.map((g) => (
              <div
                key={g.id}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border/60 pb-3 last:border-0 last:pb-0"
              >
                <div>
                  <p className="font-medium">{g.route}</p>
                  <p className="text-xs text-muted-foreground">
                    Recent cut-off {g.typical_cutoff} · {g.itas_last_12_months.toLocaleString()}{" "}
                    invitations in 12 months
                  </p>
                </div>
                <Badge variant={g.clears ? "default" : "outline"} className="tabular-nums">
                  {g.gap >= 0 ? `+${g.gap} clear` : `${Math.abs(g.gap)} short`}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {ineligible.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Routes you do not qualify for yet</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {ineligible.map((g) => (
              <div key={g.id} className="flex flex-wrap justify-between gap-2">
                <span className="font-medium">{g.route}</span>
                <span className="text-muted-foreground">{g.eligibility_reason}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {dormant.length > 0 && (
        <Card className="border-amber-500/40">
          <CardHeader>
            <CardTitle className="text-base">Listed by IRCC, but not being drawn</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex flex-wrap gap-1">
              {dormant.map((d) => (
                <Badge key={d.id} variant="outline">
                  {d.label}
                </Badge>
              ))}
            </div>
            <p className="text-muted-foreground">
              These categories appear on IRCC&apos;s published list, but no round has been held in
              the last 12 months. Eligibility for a dormant category does not produce an invitation.
            </p>
          </CardContent>
        </Card>
      )}

      {report.next_moves && report.next_moves.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">What would change your situation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {report.next_moves.map((m, i) => (
              <div key={i} className="border-b border-border/60 pb-3 last:border-0 last:pb-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium">{m.action}</p>
                  <Badge variant="secondary" className="tabular-nums">
                    up to +{m.points}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{m.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {crs && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Score breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {Object.entries(crs.breakdown)
                .filter(([, v]) => typeof v === "number")
                .map(([key, value]) => (
                  <li key={key} className="flex justify-between gap-3">
                    <span className="text-muted-foreground">
                      {BREAKDOWN_LABELS[key] || key.replace(/_/g, " ")}
                    </span>
                    <span className="tabular-nums">{value}</span>
                  </li>
                ))}
            </ul>
            <div className="mt-4 flex justify-between border-t border-border pt-3 font-semibold">
              <span>Total</span>
              <span className="tabular-nums">{crs.total}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Experience</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="text-3xl font-bold tabular-nums">
              {summary?.canadian_experience_months ?? 0}
            </p>
            <p className="text-muted-foreground">months of Canadian experience</p>
            {summary?.primary_noc && (
              <p className="mt-2">
                Primary NOC {summary.primary_noc} (TEER {summary.primary_teer})
              </p>
            )}
            {typeof report.permit_runway_days === "number" && (
              <p className="mt-2 text-amber-700 dark:text-amber-300">
                Permit expires in {report.permit_runway_days} days.
              </p>
            )}
          </CardContent>
        </Card>

        {report.arranged_employment_note && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">About job offers</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {report.arranged_employment_note}
            </CardContent>
          </Card>
        )}
      </div>

      {report.draws_metadata?.last_verified && (
        <p className="text-center text-xs text-muted-foreground">
          Draw data verified {report.draws_metadata.last_verified}.
          {crs?.grid_version && ` CRS grid version ${crs.grid_version}.`}
        </p>
      )}
    </div>
  );
}
