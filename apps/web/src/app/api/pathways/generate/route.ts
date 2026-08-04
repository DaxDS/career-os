import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import {
  DISCLAIMER,
  calculateCrs,
  drawLandscape,
  evaluateEligibility,
  gapAnalysis,
  headline,
  nextMoves,
  profileToCrs,
  referenceMetadata,
} from "@/lib/crs/report";

export const runtime = "nodejs";

/**
 * Generate a PR pathway report.
 *
 * Runs the CRS engine in-process. This previously proxied to a Python agent at
 * AGENT_SERVICE_URL, which is not deployed — the call fell through to
 * http://localhost:8000 and every request returned 503. The report is the product's
 * core promise, so it cannot depend on a service that does not exist.
 */

function monthsBetween(start: string | null, end: string | null, isCurrent: boolean): number {
  if (!start) return 0;
  const s = new Date(`${start.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(s.getTime())) return 0;
  const e = isCurrent || !end ? new Date() : new Date(`${end.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(e.getTime())) return 0;
  const months = (e.getUTCFullYear() - s.getUTCFullYear()) * 12 + (e.getUTCMonth() - s.getUTCMonth());
  return Math.max(0, months);
}

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const { data: profile, error: profileError } = await supabase
      .from("profiles")
      .select("*")
      .eq("id", user.id)
      .single();

    if (profileError || !profile) {
      return NextResponse.json({ error: "Profile not found. Complete onboarding first." }, { status: 404 });
    }

    const { data: workHistory } = await supabase
      .from("work_history")
      .select("*")
      .eq("user_id", user.id)
      .order("sort_order");

    const history = workHistory ?? [];

    let canadianMonths = 0;
    let foreignMonths = 0;
    const canadianMonthsByNoc: Record<string, number> = {};

    for (const wh of history) {
      const months =
        (wh.months_canadian_experience as number | null) ??
        monthsBetween(wh.start_date, wh.end_date, Boolean(wh.is_current));
      const country = String(wh.country ?? "CA").toUpperCase();
      if (country === "CA" || country === "CANADA") {
        canadianMonths += months;
        const noc = wh.mapped_noc_code as string | null;
        if (noc) canadianMonthsByNoc[noc] = (canadianMonthsByNoc[noc] ?? 0) + months;
      } else {
        foreignMonths += months;
      }
    }

    // Foreign experience entered directly on the profile counts when no foreign work
    // history rows exist, so a newcomer who typed "3 years abroad" is not scored as zero.
    if (foreignMonths === 0 && typeof profile.foreign_experience_months === "number") {
      foreignMonths = profile.foreign_experience_months;
    }

    let primaryNoc: string | null = null;
    let primaryTeer: number | null = null;
    const nocEntries = Object.entries(canadianMonthsByNoc);
    if (nocEntries.length) {
      primaryNoc = nocEntries.reduce((a, b) => (b[1] > a[1] ? b : a))[0];
      const match = history.find((w) => w.mapped_noc_code === primaryNoc);
      primaryTeer = (match?.mapped_teer as number | null) ?? null;
    }

    const crsProfile = profileToCrs(profile, canadianMonths, foreignMonths);
    const crs = calculateCrs(crsProfile);

    const landscape = drawLandscape();
    const eligibility = evaluateEligibility({
      profile: crsProfile,
      canadianMonths,
      foreignMonths,
      canadianMonthsByNoc,
      primaryTeer,
      hasNomination: Boolean(profile.has_provincial_nomination),
    });
    const gaps = gapAnalysis(crs.total, landscape, eligibility);

    const report = {
      generated_at: new Date().toISOString(),
      disclaimer: DISCLAIMER,
      headline: headline(crs.total, gaps),
      crs: {
        total: crs.total,
        core: crs.core,
        spouse: crs.spouse,
        transferability: crs.transferability,
        additional: crs.additional,
        breakdown: crs.breakdown,
        grid_version: crs.gridVersion,
      },
      profile_summary: {
        status: profile.status,
        province: profile.province,
        permit_expiry: profile.permit_expiry,
        canadian_experience_months: canadianMonths,
        foreign_experience_months: foreignMonths,
        primary_noc: primaryNoc,
        primary_teer: primaryTeer,
      },
      draw_landscape: {
        live: landscape.live.map((r) => ({
          id: r.id,
          label: r.label,
          rounds_last_12_months: r.roundsLast12Months,
          itas_last_12_months: r.itasLast12Months,
          last_drawn: r.lastDrawn,
          typical_cutoff: r.typicalCutoff,
        })),
        dormant: landscape.dormant.map((r) => ({ id: r.id, label: r.label, warning: r.warning })),
      },
      eligibility,
      gap_analysis: gaps,
      next_moves: nextMoves(crs, canadianMonths, Boolean(profile.has_provincial_nomination)),
      arranged_employment_note:
        "IRCC removed arranged-employment CRS points on 2025-03-25. A job offer adds no points on its own; " +
        "its value is the Canadian experience and category or provincial eligibility it unlocks.",
      draws_metadata: referenceMetadata,
      crs_profile_completed: Boolean(profile.crs_profile_completed),
    } as Record<string, unknown>;

    if (profile.status === "pgwp" && profile.permit_expiry) {
      const expiry = new Date(`${String(profile.permit_expiry).slice(0, 10)}T00:00:00Z`);
      if (!Number.isNaN(expiry.getTime())) {
        report.permit_runway_days = Math.round((expiry.getTime() - Date.now()) / 86_400_000);
      }
    }

    // Persisted with the service role: the report is a server-generated artifact and
    // users have no insert policy on pathway_reports.
    try {
      await createAdminClient().from("pathway_reports").insert({ user_id: user.id, report_json: report });
    } catch (persistError) {
      // A failed archive must not deny the user their report.
      console.error("[pathways/generate] persist failed", persistError);
    }

    return NextResponse.json(report);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to generate report";
    console.error("[pathways/generate]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
