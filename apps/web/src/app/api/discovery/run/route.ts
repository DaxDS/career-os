import { NextResponse } from "next/server";
import { createHash } from "node:crypto";

import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity-log";
import { searchJobBank } from "@/lib/jobs/jobbank";
import { scoreJobForPr } from "@/lib/jobs/score";
import { profileToCrs } from "@/lib/crs/report";
import { teerFromNocCode } from "@/lib/crs/noc";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Discover jobs and score them by PR impact.
 *
 * Runs in-process against Job Bank. This previously proxied to a Python agent at
 * AGENT_SERVICE_URL which is not deployed, so the jobs feed returned 503 for every
 * user. Job Bank is the only configured source needing no API key, which is what
 * makes the feed shippable without new credentials.
 */

const DEFAULT_KEYWORDS = ["software developer", "administrative assistant", "general labourer"];

function monthsBetween(start: string | null, end: string | null, isCurrent: boolean): number {
  if (!start) return 0;
  const s = new Date(`${start.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(s.getTime())) return 0;
  const e = isCurrent || !end ? new Date() : new Date(`${end.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(e.getTime())) return 0;
  return Math.max(0, (e.getUTCFullYear() - s.getUTCFullYear()) * 12 + (e.getUTCMonth() - s.getUTCMonth()));
}

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const { data: profile } = await supabase.from("profiles").select("*").eq("id", user.id).single();
    if (!profile) {
      return NextResponse.json({ error: "Complete onboarding first." }, { status: 400 });
    }

    const { data: workHistory } = await supabase
      .from("work_history")
      .select("*")
      .eq("user_id", user.id)
      .order("sort_order");

    let canadianMonths = 0;
    let foreignMonths = 0;
    for (const wh of workHistory ?? []) {
      const fromDates = monthsBetween(wh.start_date, wh.end_date, Boolean(wh.is_current));
      const stored = typeof wh.months_canadian_experience === "number" ? wh.months_canadian_experience : 0;
      const months = fromDates > 0 ? fromDates : stored;
      if (String(wh.country ?? "CA").toUpperCase().startsWith("CA")) canadianMonths += months;
      else foreignMonths += months;
    }
    if (foreignMonths === 0 && typeof profile.foreign_experience_months === "number") {
      foreignMonths = profile.foreign_experience_months;
    }

    const crsProfile = profileToCrs(profile, canadianMonths, foreignMonths);

    const targets = Array.isArray(profile.target_titles) ? (profile.target_titles as string[]) : [];
    const keywords = (targets.length ? targets : DEFAULT_KEYWORDS).slice(0, 3);
    const location = profile.province ? String(profile.province) : "Canada";

    await logActivity(user.id, "discovery_started", `Searching Job Bank for ${keywords.join(", ")}`, {
      keywords,
      location,
    });

    const listings = await searchJobBank(keywords, location, 12);
    if (listings.length === 0) {
      // Logged as an outcome, not silence. Job Bank scraping is regex against markup
      // we do not control and has already rotted once — a run that quietly returns
      // nothing is indistinguishable from a broken scraper unless it is recorded.
      await logActivity(
        user.id,
        "discovery_completed",
        `No postings returned for ${keywords.join(", ")}`,
        { keywords, location, found: 0 }
      );
      return NextResponse.json({
        discovered: 0,
        matched: 0,
        message:
          "No postings came back from Job Bank for those search terms. Try different target job titles in your profile.",
      });
    }

    const admin = createAdminClient();
    let matched = 0;

    for (const listing of listings) {
      const dedupeHash = createHash("sha256")
        .update(`${listing.source}:${listing.externalId}`)
        .digest("hex");

      const teer = listing.nocCode ? teerFromNocCode(listing.nocCode) : null;

      // Upsert on dedupe_hash so re-running discovery refreshes rather than duplicates.
      const { data: job, error: jobError } = await admin
        .from("jobs")
        .upsert(
          {
            source: listing.source,
            external_id: listing.externalId,
            url: listing.url,
            title: listing.title,
            company: listing.company,
            city: listing.city,
            province: listing.province,
            raw_jd: listing.description,
            noc_code: listing.nocCode,
            teer_level: teer,
            dedupe_hash: dedupeHash,
            updated_at: new Date().toISOString(),
          },
          { onConflict: "dedupe_hash" }
        )
        .select("id")
        .single();

      if (jobError || !job) {
        console.error("[discovery] job upsert failed:", jobError?.message);
        continue;
      }

      const score = scoreJobForPr(crsProfile, {
        nocCode: listing.nocCode,
        teerLevel: teer,
        province: listing.province,
        title: listing.title,
      });

      const { error: matchError } = await admin.from("matches").upsert(
        {
          user_id: user.id,
          job_id: job.id,
          match_score: score.matchScore,
          score_breakdown: score as unknown as Record<string, unknown>,
          pathway_flags: {
            unlocked_categories: score.unlockedCategories,
            dormant_but_eligible: score.dormantButEligible,
            cec_eligible: score.cecEligible,
          },
          updated_at: new Date().toISOString(),
        },
        { onConflict: "user_id,job_id" }
      );

      if (matchError) {
        console.error("[discovery] match upsert failed:", matchError.message);
        continue;
      }
      matched += 1;
    }

    await logActivity(
      user.id,
      "discovery_completed",
      `Found ${listings.length} postings, scored ${matched} into your feed`,
      { keywords, location, found: listings.length, matched }
    );

    return NextResponse.json({ discovered: listings.length, matched });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Discovery failed";
    console.error("[discovery]", message);
    await logActivity(user.id, "discovery_failed", "Job discovery failed", { error: message });
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
