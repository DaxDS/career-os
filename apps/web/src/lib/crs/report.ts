/**
 * PR pathway report: CRS score, live draw landscape, eligibility-gated gaps, next moves.
 *
 * Port of services/agent/graphs/pathway_report.py. Three rules carry over:
 *
 *  1. Every claim carries its evidence — scores show breakdowns, cut-offs show dates.
 *  2. Dormant categories are called dormant. Being on IRCC's published list means
 *     nothing if no round has been held.
 *  3. Unverified data never becomes advice. If a category's NOC list has not been
 *     checked against IRCC, the report says so rather than guessing.
 *
 * Informational only. Not immigration advice.
 */

import reference from "./reference-data.json";
import type { ProvincialOutlook } from "./provinces";
import {
  ageFrom,
  calculateCrs,
  minAbility,
  type CrsProfile,
  type CrsResult,
  type EducationLevel,
  type LanguageScores,
  ZERO_LANGUAGE,
} from "./grid";

export const DISCLAIMER =
  "This is informational only, based on published program criteria, and is not immigration advice. " +
  "Consult a licensed RCIC or immigration lawyer for decisions.";

const DORMANCY_WINDOW_MONTHS = 12;
const CATEGORY_MIN_MONTHS = 12;
const CEC_MIN_MONTHS = 12;
const CEC_ELIGIBLE_TEERS = new Set([0, 1, 2, 3]);

const PROGRAM_LABELS: Record<string, string> = {
  general: "General (all-program) round",
  cec: "Canadian Experience Class",
  fsw: "Federal Skilled Worker",
  fst: "Federal Skilled Trades",
  pnp: "Provincial Nominee Program",
};

interface Draw {
  round: number;
  date: string;
  category: string;
  itas: number;
  crs_cutoff: number;
}

interface Category {
  id: string;
  draw_category_id?: string;
  label: string;
  verification_status?: string;
  requires_canadian_experience?: boolean;
  noc_codes?: string[];
  all_teer_0_3?: boolean;
  requires_french_nclc_min?: number;
  exclude_from_job_scoring?: boolean;
}

const DRAWS = (reference.draws as Draw[]).slice().sort((a, b) => b.date.localeCompare(a.date));
const CATEGORIES = reference.categories as Category[];
const CATEGORY_IDS = reference.categoryIds as string[];

function withinWindow(dateStr: string, months: number): boolean {
  const cutoff = new Date();
  cutoff.setUTCMonth(cutoff.getUTCMonth() - months);
  return new Date(`${dateStr}T00:00:00Z`) >= cutoff;
}

function median(values: number[]): number {
  const s = values.slice().sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : Math.floor((s[mid - 1] + s[mid]) / 2);
}

export interface CategoryActivity {
  rounds: number;
  totalItas: number;
  lastDrawn: string | null;
  /** Median of the most recent rounds — a single 4-ITA round can sit tens of points off. */
  typicalCutoff: number | null;
}

export function categoryActivity(category: string, months = DORMANCY_WINDOW_MONTHS): CategoryActivity {
  const inWindow = DRAWS.filter((d) => d.category === category && withinWindow(d.date, months));
  const recent = DRAWS.filter((d) => d.category === category).slice(0, 3);
  return {
    rounds: inWindow.length,
    totalItas: inWindow.reduce((s, d) => s + (d.itas || 0), 0),
    lastDrawn: inWindow[0]?.date ?? null,
    typicalCutoff: recent.length ? median(recent.map((r) => r.crs_cutoff)) : null,
  };
}

export interface RouteRow {
  id: string;
  label: string;
  roundsLast12Months: number;
  itasLast12Months: number;
  lastDrawn: string | null;
  typicalCutoff: number | null;
  warning?: string;
}

export function drawLandscape(): { live: RouteRow[]; dormant: RouteRow[] } {
  const byDrawId = new Map<string, Category>();
  for (const c of CATEGORIES) byDrawId.set(c.draw_category_id || c.id, c);

  const live: RouteRow[] = [];
  const dormant: RouteRow[] = [];

  for (const id of CATEGORY_IDS) {
    const stats = categoryActivity(id);
    const meta = byDrawId.get(id);
    const row: RouteRow = {
      id,
      label: meta?.label || PROGRAM_LABELS[id] || id.replace(/_/g, " "),
      roundsLast12Months: stats.rounds,
      itasLast12Months: stats.totalItas,
      lastDrawn: stats.lastDrawn,
      typicalCutoff: stats.typicalCutoff,
    };
    if (stats.rounds > 0) live.push(row);
    else {
      row.warning =
        `Listed by IRCC as a current category, but no round has been held in the last ` +
        `${DORMANCY_WINDOW_MONTHS} months. Being eligible for a dormant category does not produce an invitation.`;
      dormant.push(row);
    }
  }

  live.sort((a, b) => b.itasLast12Months - a.itasLast12Months);
  return { live, dormant };
}

export interface Eligibility {
  eligible: boolean;
  reason: string;
  needsVerification?: boolean;
}

/**
 * Whether the candidate qualifies for each route, independent of score.
 *
 * Resolved before any gap analysis. Comparing a score against a category the candidate
 * cannot enter produces a confident, precise, wrong answer.
 */
export function evaluateEligibility(args: {
  profile: CrsProfile;
  canadianMonths: number;
  foreignMonths: number;
  canadianMonthsByNoc: Record<string, number>;
  primaryTeer: number | null;
  hasNomination: boolean;
}): Record<string, Eligibility> {
  const { profile, canadianMonths, foreignMonths, canadianMonthsByNoc, primaryTeer, hasNomination } = args;
  const out: Record<string, Eligibility> = {};
  const totalMonths = canadianMonths + foreignMonths;

  for (const cat of CATEGORIES) {
    const id = cat.draw_category_id || cat.id;

    if (cat.exclude_from_job_scoring) {
      out[id] = {
        eligible: false,
        reason: "Eligibility depends on a Canadian Armed Forces job offer, which this profile cannot confirm.",
      };
      continue;
    }

    if (cat.all_teer_0_3) {
      const need = cat.requires_french_nclc_min ?? 7;
      const hasFrench = minAbility(profile.secondLanguage) >= need;
      const enough = totalMonths >= CATEGORY_MIN_MONTHS;
      const teerOk = primaryTeer !== null && primaryTeer <= 3;
      out[id] = {
        eligible: hasFrench && enough && teerOk,
        reason:
          hasFrench && enough && teerOk
            ? "NCLC 7+ French with TEER 0-3 experience on file."
            : !hasFrench
              ? `Needs NCLC ${need}+ in all four French abilities.`
              : `Needs ${CATEGORY_MIN_MONTHS} months of TEER 0-3 experience.`,
      };
      continue;
    }

    if (cat.verification_status !== "verified") {
      out[id] = {
        eligible: false,
        reason: "This category's occupation list has not been verified against IRCC, so eligibility cannot be asserted.",
        needsVerification: true,
      };
      continue;
    }

    const codes = new Set(cat.noc_codes || []);
    const months = Object.entries(canadianMonthsByNoc)
      .filter(([noc]) => codes.has(noc))
      .reduce((s, [, m]) => s + m, 0);

    out[id] = {
      eligible: months >= CATEGORY_MIN_MONTHS,
      reason:
        months >= CATEGORY_MIN_MONTHS
          ? `${months} months of experience in an eligible occupation.`
          : `Needs ${CATEGORY_MIN_MONTHS} months in an eligible occupation; you have ${months}.`,
    };
  }

  const cecOk = canadianMonths >= CEC_MIN_MONTHS && primaryTeer !== null && CEC_ELIGIBLE_TEERS.has(primaryTeer);
  out.cec = {
    eligible: cecOk,
    reason: cecOk
      ? `${canadianMonths} months of Canadian TEER ${primaryTeer} experience.`
      : `Needs ${CEC_MIN_MONTHS} months of Canadian TEER 0-3 experience; you have ${canadianMonths}.`,
  };

  out.pnp = {
    eligible: hasNomination,
    reason: hasNomination
      ? "Provincial nomination on file."
      : "PNP round cut-offs apply only to candidates who already hold a nomination.",
  };

  for (const program of ["general", "fsw", "fst"]) {
    if (!out[program]) out[program] = { eligible: false, reason: "No round held in the reporting window." };
  }

  return out;
}

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

export function gapAnalysis(
  crsTotal: number,
  landscape: { live: RouteRow[] },
  eligibility: Record<string, Eligibility>
): GapRow[] {
  const gaps: GapRow[] = [];
  for (const cat of landscape.live) {
    if (cat.typicalCutoff === null) continue;
    const e = eligibility[cat.id] ?? { eligible: false, reason: "Eligibility unknown." };
    gaps.push({
      route: cat.label,
      id: cat.id,
      typical_cutoff: cat.typicalCutoff,
      your_score: crsTotal,
      gap: crsTotal - cat.typicalCutoff,
      score_clears_cutoff: crsTotal >= cat.typicalCutoff,
      eligible: e.eligible,
      eligibility_reason: e.reason,
      clears: e.eligible && crsTotal >= cat.typicalCutoff,
      itas_last_12_months: cat.itasLast12Months,
      last_drawn: cat.lastDrawn,
    });
  }
  gaps.sort((a, b) => (a.eligible === b.eligible ? b.gap - a.gap : a.eligible ? -1 : 1));
  return gaps;
}

export interface NextMove {
  action: string;
  points: number;
  effort: "low" | "medium" | "high";
  detail: string;
}

export function nextMoves(
  crs: CrsResult,
  canadianMonths: number,
  hasNomination: boolean,
  outlook?: ProvincialOutlook
): NextMove[] {
  const moves: NextMove[] = [];
  const b = crs.breakdown;

  if (!hasNomination) {
    // Name the province and stream. "Pursue a provincial nomination" is advice nobody
    // can act on — the actionable unit is "Alberta Express Entry Stream, no job offer
    // required, health care is a named pathway".
    const best = outlook?.matches.find((m) => m.streams.some((s) => s.fit === "strong"));
    const stream = best?.streams.find((s) => s.fit === "strong");

    moves.push({
      action: stream ? `Apply to ${best!.name}: ${stream.label}` : "Pursue a provincial nomination",
      points: 600,
      effort: stream?.requiresJobOffer === false ? "medium" : "high",
      detail: stream
        ? `A nomination adds 600 CRS points and effectively guarantees an invitation. ` +
          `Your strongest published route is ${best!.program} — ${stream.label}. ` +
          stream.reasons.join(" ")
        : "A nomination adds 600 CRS points and effectively guarantees an invitation. No province " +
          "currently publishes a stream you clear outright, so the realistic paths are a qualifying " +
          "job offer or moving into an occupation a province is actively inviting. See the provincial " +
          "breakdown below for which is closest.",
    });
  }

  if ((b.first_language ?? 0) < 128) {
    moves.push({
      action: "Retake your English test to reach CLB 9 in all four abilities",
      points: 128 - (b.first_language ?? 0),
      effort: "medium",
      detail:
        `You currently score ${b.first_language ?? 0} of a possible 136 on first-language points. CLB 9 also ` +
        "unlocks the higher skill-transferability tiers, so the real gain is usually larger than the language points alone.",
    });
  }

  if ((b.french_bonus ?? 0) === 0) {
    moves.push({
      action: "Reach NCLC 7 in French",
      points: 50,
      effort: "high",
      detail:
        "French draws have been the most heavily used category, with cut-offs far below the Canadian " +
        "Experience Class. This is the highest-volume route currently open.",
    });
  }

  if (canadianMonths < 12) {
    moves.push({
      action: `Complete 12 months of Canadian TEER 0-3 work (${12 - canadianMonths} to go)`,
      points: 40,
      effort: "medium",
      detail:
        "Twelve months opens the Canadian Experience Class and satisfies the current category-based " +
        "experience threshold, which rose from 6 months to 12.",
    });
  } else if (canadianMonths < 36) {
    moves.push({
      action: "Keep accruing Canadian experience",
      points: 24,
      effort: "low",
      detail:
        `You have ${canadianMonths} months. Years two and three are worth roughly 13 and 11 more core points, ` +
        "plus transferability gains.",
    });
  }

  if ((b.canadian_study ?? 0) === 0) {
    moves.push({
      action: "Claim points for Canadian post-secondary study, if you have it",
      points: 30,
      effort: "low",
      detail: "Worth 15 points for a one- or two-year credential, 30 for three years or more.",
    });
  }

  if ((b.sibling_in_canada ?? 0) === 0) {
    moves.push({
      action: "Claim the sibling bonus, if you have a sibling who is a citizen or PR",
      points: 15,
      effort: "low",
      detail: "Frequently missed. Requires a sibling aged 18+ resident in Canada.",
    });
  }

  moves.sort((a, b2) => b2.points - a.points);
  return moves;
}

export function headline(crsTotal: number, gaps: GapRow[]): { crs: number; status: string; text: string } {
  const eligible = gaps.filter((g) => g.eligible);
  const clearing = eligible.filter((g) => g.score_clears_cutoff);

  if (clearing.length) {
    const best = clearing.reduce((a, b) => (b.itas_last_12_months > a.itas_last_12_months ? b : a));
    return {
      crs: crsTotal,
      status: "clears",
      text:
        `Your CRS is ${crsTotal}. That clears the recent ${best.route} cut-off of ${best.typical_cutoff} — ` +
        `a route that issued ${best.itas_last_12_months.toLocaleString("en-CA")} invitations in the last 12 months.`,
    };
  }

  if (eligible.length) {
    const closest = eligible.reduce((a, b) => (b.gap > a.gap ? b : a));
    return {
      crs: crsTotal,
      status: "short",
      text:
        `Your CRS is ${crsTotal}. The best route you currently qualify for is ${closest.route} at a recent ` +
        `cut-off of ${closest.typical_cutoff} — ${Math.abs(closest.gap)} points away.`,
    };
  }

  return {
    crs: crsTotal,
    status: "no_route",
    text:
      `Your CRS is ${crsTotal}, but you do not yet qualify for any route currently being drawn. ` +
      "Becoming eligible matters more than raising your score right now.",
  };
}

/** Map a profiles row + work history into the CRS profile shape. */
export function profileToCrs(
  row: Record<string, unknown>,
  canadianMonths: number,
  foreignMonths: number
): CrsProfile {
  const num = (v: unknown) => (typeof v === "number" ? v : 0);
  const lang = (prefix: string): LanguageScores => ({
    reading: num(row[`${prefix}_reading`]),
    writing: num(row[`${prefix}_writing`]),
    listening: num(row[`${prefix}_listening`]),
    speaking: num(row[`${prefix}_speaking`]),
  });

  const hasSpouse = Boolean(row.has_accompanying_spouse);
  const education = (row.education_level as EducationLevel) || "none";

  return {
    age: ageFrom((row.date_of_birth as string) ?? null),
    education,
    firstLanguage: lang("clb_en"),
    secondLanguage: lang("nclc_fr"),
    canadianExperienceYears: Math.floor(canadianMonths / 12),
    foreignExperienceYears: Math.floor(foreignMonths / 12),
    hasSpouse,
    spouse: hasSpouse
      ? {
          education: (row.spouse_education_level as EducationLevel) || "none",
          firstLanguage: {
            reading: num(row.spouse_clb_reading),
            writing: num(row.spouse_clb_writing),
            listening: num(row.spouse_clb_listening),
            speaking: num(row.spouse_clb_speaking),
          },
          canadianExperienceYears: num(row.spouse_canadian_experience_years),
        }
      : null,
    provincialNomination: Boolean(row.has_provincial_nomination),
    siblingInCanada: Boolean(row.sibling_in_canada),
    canadianStudyCredential:
      (row.canadian_study_credential as "one_or_two_year" | "three_year_plus" | null) ?? null,
    tradesCertificate: Boolean(row.trades_certificate),
  };
}

export const referenceMetadata = reference.metadata as {
  last_verified?: string;
  source_url?: string;
  disclaimer?: string;
};

export { calculateCrs, ZERO_LANGUAGE };
