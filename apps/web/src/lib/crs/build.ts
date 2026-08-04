import type { SupabaseClient } from "@supabase/supabase-js";

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
} from "./report";

/**
 * Build a PR pathway report from a user's stored profile and work history.
 *
 * Pure computation over data already in Postgres — no external service, no network
 * beyond the two reads. That is deliberate: the report is the product's core promise,
 * so rendering it must not depend on a background job, a separate service, or a
 * successful write. Persistence is an archive, not a prerequisite.
 */

function monthsBetween(start: string | null, end: string | null, isCurrent: boolean): number {
  if (!start) return 0;
  const s = new Date(`${start.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(s.getTime())) return 0;
  const e = isCurrent || !end ? new Date() : new Date(`${end.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(e.getTime())) return 0;
  return Math.max(0, (e.getUTCFullYear() - s.getUTCFullYear()) * 12 + (e.getUTCMonth() - s.getUTCMonth()));
}

export interface BuiltReport {
  report: Record<string, unknown> | null;
  error: string | null;
}

export async function buildPathwayReport(
  supabase: SupabaseClient,
  userId: string
): Promise<BuiltReport> {
  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", userId)
    .single();

  if (profileError || !profile) {
    return { report: null, error: "Profile not found. Complete onboarding first." };
  }

  const { data: workHistory } = await supabase
    .from("work_history")
    .select("*")
    .eq("user_id", userId)
    .order("sort_order");

  const history = workHistory ?? [];

  let canadianMonths = 0;
  let foreignMonths = 0;
  const canadianMonthsByNoc: Record<string, number> = {};

  for (const wh of history) {
    // months_canadian_experience is NOT NULL DEFAULT 0, so `?? computed` would never
    // fall through — 0 is not nullish. Dates win when present; the stored figure is
    // only a fallback for rows that predate date capture.
    const fromDates = monthsBetween(wh.start_date, wh.end_date, Boolean(wh.is_current));
    const stored = typeof wh.months_canadian_experience === "number" ? wh.months_canadian_experience : 0;
    const months = fromDates > 0 ? fromDates : stored;
    const country = String(wh.country ?? "CA").toUpperCase();
    if (country === "CA" || country === "CANADA") {
      canadianMonths += months;
      const noc = wh.mapped_noc_code as string | null;
      if (noc) canadianMonthsByNoc[noc] = (canadianMonthsByNoc[noc] ?? 0) + months;
    } else {
      foreignMonths += months;
    }
  }

  // Profile-level foreign experience is a fallback for users who typed "3 years
  // abroad" rather than entering foreign work-history rows.
  if (foreignMonths === 0 && typeof profile.foreign_experience_months === "number") {
    foreignMonths = profile.foreign_experience_months;
  }

  // An explicit Canadian figure wins over the dated history. Canadian experience is
  // worth up to 80 core points and gates CEC and every category round, so the user
  // must be able to state it directly rather than depend on complete date entry.
  const declaredCanadian = profile.canadian_experience_months;
  if (typeof declaredCanadian === "number" && declaredCanadian > 0) {
    canadianMonths = declaredCanadian;
  }

  let primaryNoc: string | null = null;
  let primaryTeer: number | null = null;
  const nocEntries = Object.entries(canadianMonthsByNoc);
  if (nocEntries.length) {
    primaryNoc = nocEntries.reduce((a, b) => (b[1] > a[1] ? b : a))[0];
    primaryTeer = (history.find((w) => w.mapped_noc_code === primaryNoc)?.mapped_teer as number | null) ?? null;
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

  const report: Record<string, unknown> = {
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
  };

  if (profile.status === "pgwp" && profile.permit_expiry) {
    const expiry = new Date(`${String(profile.permit_expiry).slice(0, 10)}T00:00:00Z`);
    if (!Number.isNaN(expiry.getTime())) {
      report.permit_runway_days = Math.round((expiry.getTime() - Date.now()) / 86_400_000);
    }
  }

  return { report, error: null };
}

/**
 * Archive a report. Best effort — a failed write must never deny the user their score.
 *
 * supabase-js returns errors rather than throwing them, so the returned `error` has to
 * be inspected explicitly. Wrapping this in try/catch alone silently swallows failures.
 */
export async function archiveReport(
  admin: SupabaseClient,
  userId: string,
  report: Record<string, unknown>
): Promise<string | null> {
  try {
    const { error } = await admin.from("pathway_reports").insert({ user_id: userId, report_json: report });
    if (error) {
      console.error("[pathways] archive failed:", error.message, error.details ?? "", error.hint ?? "");
      return error.message;
    }
    return null;
  } catch (thrown) {
    const message = thrown instanceof Error ? thrown.message : String(thrown);
    console.error("[pathways] archive threw:", message);
    return message;
  }
}
