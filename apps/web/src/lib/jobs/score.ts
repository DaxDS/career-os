import referenceData from "@/lib/crs/reference-data.json";
import { calculateCrs, type CrsProfile } from "@/lib/crs/grid";
import { categoryActivity } from "@/lib/crs/report";
import { teerFromNocCode } from "@/lib/crs/noc";

/**
 * Score a job by how far it moves a candidate toward permanent residence.
 *
 * Since IRCC removed arranged-employment points on 2025-03-25, a job offer is worth
 * zero CRS points. A job can only help three ways, and this scores exactly those:
 * accruing Canadian experience, opening a category-based round, and satisfying the
 * Canadian Experience Class threshold.
 *
 * Informational only. Not immigration advice.
 */

const CATEGORY_MIN_MONTHS = 12;
const CEC_ELIGIBLE_TEERS = new Set([0, 1, 2, 3]);

interface Category {
  id: string;
  draw_category_id?: string;
  label: string;
  verification_status?: string;
  noc_codes?: string[];
  all_teer_0_3?: boolean;
  min_teer?: number;
  max_teer?: number;
  exclude_from_job_scoring?: boolean;
}

const CATEGORIES = referenceData.categories as Category[];

export interface JobContext {
  nocCode: string | null;
  teerLevel: number | null;
  province: string | null;
  title: string;
}

export interface JobScore {
  /** 0-100, driven by PR impact rather than keyword overlap. */
  matchScore: number;
  crsNow: number;
  crsAfter12Months: number;
  crsDelta: number;
  unlockedCategories: Array<{ id: string; label: string; itas: number; cutoff: number | null }>;
  dormantButEligible: string[];
  cecEligible: boolean;
  cecGap: number | null;
  verdict: string;
  arrangedEmploymentPoints: 0;
}

function withExtraYear(profile: CrsProfile): CrsProfile {
  return {
    ...profile,
    canadianExperienceYears: Math.min(profile.canadianExperienceYears + 1, 5),
  };
}

export function scoreJobForPr(profile: CrsProfile, job: JobContext): JobScore {
  const crsNow = calculateCrs(profile).total;
  const crsAfter = calculateCrs(withExtraYear(profile)).total;
  const teer = job.teerLevel ?? (job.nocCode ? teerFromNocCode(job.nocCode) : null);

  const unlocked: JobScore["unlockedCategories"] = [];
  const dormant: string[] = [];

  for (const cat of CATEGORIES) {
    if (cat.exclude_from_job_scoring) continue;
    // Unverified NOC lists must never assert eligibility.
    if (cat.verification_status !== "verified") continue;
    if (cat.all_teer_0_3) continue; // French category keys off language, not the job.
    if (!job.nocCode) continue;

    const codes = new Set(cat.noc_codes ?? []);
    if (!codes.has(job.nocCode)) continue;
    if (teer !== null) {
      const min = cat.min_teer ?? 0;
      const max = cat.max_teer ?? 5;
      if (teer < min || teer > max) continue;
    }

    const activity = categoryActivity(cat.draw_category_id || cat.id);
    if (activity.rounds > 0) {
      unlocked.push({
        id: cat.id,
        label: cat.label,
        itas: activity.totalItas,
        cutoff: activity.typicalCutoff,
      });
    } else {
      // Eligible but nobody has been invited — reported, never sold as an opportunity.
      dormant.push(cat.label);
    }
  }

  const cecActivity = categoryActivity("cec");
  const cecEligible = teer !== null && CEC_ELIGIBLE_TEERS.has(teer);
  const cecGap = cecActivity.typicalCutoff !== null ? crsAfter - cecActivity.typicalCutoff : null;

  // Score composition: the PR delta is the product, so it dominates. A role that opens
  // a live category outranks one that merely pays well.
  let score = 0;
  score += Math.min(40, (crsAfter - crsNow) * 1.0);
  if (cecEligible) score += 25;
  if (unlocked.length > 0) score += 25;
  if (cecGap !== null && cecGap >= 0) score += 10;
  if (teer !== null && teer <= 1) score += 5;
  const matchScore = Math.max(0, Math.min(100, Math.round(score)));

  let verdict: string;
  const bestUnlocked = unlocked.slice().sort((a, b) => b.itas - a.itas)[0];
  if (bestUnlocked && bestUnlocked.cutoff !== null) {
    const gap = crsAfter - bestUnlocked.cutoff;
    verdict =
      gap >= 0
        ? `12 months here puts your CRS at ${crsAfter}, clearing the recent ${bestUnlocked.label} cut-off of ${bestUnlocked.cutoff} by ${gap}.`
        : `12 months here puts your CRS at ${crsAfter}, still ${Math.abs(gap)} short of the recent ${bestUnlocked.label} cut-off of ${bestUnlocked.cutoff}.`;
  } else if (cecEligible && cecGap !== null) {
    verdict =
      cecGap >= 0
        ? `12 months here opens the Canadian Experience Class at CRS ${crsAfter}, clearing its recent cut-off by ${cecGap}.`
        : `12 months here opens the Canadian Experience Class, but at CRS ${crsAfter} you would still be ${Math.abs(cecGap)} short.`;
  } else if (dormant.length > 0) {
    verdict = `Matches ${dormant.join(", ")}, but no round has been held there in 12 months.`;
  } else {
    verdict = "Opens no category-based or CEC route on the data available.";
  }

  return {
    matchScore,
    crsNow,
    crsAfter12Months: crsAfter,
    crsDelta: crsAfter - crsNow,
    unlockedCategories: unlocked,
    dormantButEligible: dormant,
    cecEligible,
    cecGap,
    verdict,
    arrangedEmploymentPoints: 0,
  };
}
