"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface PathwayReportData {
  generated_at?: string;
  disclaimer?: string;
  profile_summary?: {
    status?: string;
    province?: string;
    permit_expiry?: string;
    language_en?: string;
    language_fr?: string;
  };
  canadian_experience?: {
    total_months?: number;
    by_noc?: Record<string, number>;
    primary_noc?: string;
    primary_teer?: number;
  };
  pathway_flags?: {
    ee_eligible?: boolean;
    ee_categories?: string[];
    pnp_streams?: string[];
    aip_relevant?: boolean;
  };
  ee_teer_eligible?: boolean;
  recommendations?: string[];
}

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
      <div className="rounded-xl border border-dashed p-12 text-center space-y-4">
        <p className="text-muted-foreground">No pathway report yet.</p>
        <Button onClick={regenerate} disabled={loading}>
          {loading ? "Generating…" : "Generate report"}
        </Button>
      </div>
    );
  }

  const exp = report.canadian_experience;
  const flags = report.pathway_flags;

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

      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        {report.disclaimer}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Canadian experience</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{exp?.total_months ?? 0}</p>
            <p className="text-sm text-muted-foreground">months total</p>
            {exp?.primary_noc && (
              <p className="mt-2 text-sm">
                Primary NOC {exp.primary_noc} (TEER {exp.primary_teer})
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Express Entry</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Badge variant={report.ee_teer_eligible ? "default" : "outline"}>
              {report.ee_teer_eligible ? "TEER 0–3 eligible" : "TEER may not qualify for FSW"}
            </Badge>
            <div className="flex flex-wrap gap-1">
              {(flags?.ee_categories || []).map((c) => (
                <Badge key={c} variant="secondary">
                  {c.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">PNP / AIP</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1">
            {(flags?.pnp_streams || []).map((s) => (
              <Badge key={s} variant="outline">
                {s.replace(/_/g, " ")}
              </Badge>
            ))}
            {flags?.aip_relevant && <Badge>AIP relevant</Badge>}
            {!flags?.pnp_streams?.length && !flags?.aip_relevant && (
              <p className="text-sm text-muted-foreground">No stream matches from current NOC</p>
            )}
          </CardContent>
        </Card>
      </div>

      {exp?.by_noc && Object.keys(exp.by_noc).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Experience by NOC</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {Object.entries(exp.by_noc).map(([noc, months]) => (
                <li key={noc}>
                  NOC {noc}: {months} months
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {report.recommendations && report.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">What would change your situation</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-inside list-disc space-y-2 text-sm text-muted-foreground">
              {report.recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
