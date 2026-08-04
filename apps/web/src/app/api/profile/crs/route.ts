import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { EDUCATION_ORDER } from "@/lib/crs/grid";

export const runtime = "nodejs";

const CLB_FIELDS = [
  "clb_en_reading",
  "clb_en_writing",
  "clb_en_listening",
  "clb_en_speaking",
  "nclc_fr_reading",
  "nclc_fr_writing",
  "nclc_fr_listening",
  "nclc_fr_speaking",
  "spouse_clb_reading",
  "spouse_clb_writing",
  "spouse_clb_listening",
  "spouse_clb_speaking",
] as const;

const STUDY_VALUES = new Set(["one_or_two_year", "three_year_plus"]);

function clb(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  // Clamped rather than rejected: the database CHECK would 500 on an out-of-range
  // value, and a slider that reports 13 should not cost the user their whole form.
  return Math.min(12, Math.max(0, Math.round(n)));
}

function education(value: unknown): string | null {
  return typeof value === "string" && (EDUCATION_ORDER as readonly string[]).includes(value) ? value : null;
}

/** Save the CRS inputs. Only known fields are written; anything else is ignored. */
export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const update: Record<string, unknown> = {};

  if (body.date_of_birth) {
    const dob = String(body.date_of_birth).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dob)) {
      return NextResponse.json({ error: "date_of_birth must be YYYY-MM-DD" }, { status: 400 });
    }
    update.date_of_birth = dob;
  }

  const edu = education(body.education_level);
  if (edu) update.education_level = edu;

  const spouseEdu = education(body.spouse_education_level);
  if (spouseEdu) update.spouse_education_level = spouseEdu;

  for (const field of CLB_FIELDS) {
    if (field in body) {
      const v = clb(body[field]);
      if (v !== null) update[field] = v;
    }
  }

  for (const flag of [
    "has_accompanying_spouse",
    "has_provincial_nomination",
    "sibling_in_canada",
    "trades_certificate",
  ]) {
    if (flag in body) update[flag] = Boolean(body[flag]);
  }

  if ("spouse_canadian_experience_years" in body) {
    const n = Number(body.spouse_canadian_experience_years);
    if (Number.isFinite(n)) update.spouse_canadian_experience_years = Math.min(50, Math.max(0, Math.round(n)));
  }

  for (const field of ["foreign_experience_months", "canadian_experience_months"]) {
    if (field in body) {
      const n = Number(body[field]);
      if (Number.isFinite(n)) update[field] = Math.max(0, Math.round(n));
    }
  }

  if ("canadian_study_credential" in body) {
    const v = body.canadian_study_credential;
    update.canadian_study_credential = typeof v === "string" && STUDY_VALUES.has(v) ? v : null;
  }

  if (Object.keys(update).length === 0) {
    return NextResponse.json({ error: "No recognised fields to update" }, { status: 400 });
  }

  // Only mark the profile complete once the three factors the grid cannot work
  // without are present. A partial save is still saved, just not flagged complete.
  const { data: current } = await supabase
    .from("profiles")
    .select("date_of_birth, education_level, clb_en_reading")
    .eq("id", user.id)
    .single();

  const merged = { ...current, ...update };
  update.crs_profile_completed = Boolean(
    merged?.date_of_birth && merged?.education_level && typeof merged?.clb_en_reading === "number"
  );

  const { error } = await supabase.from("profiles").update(update).eq("id", user.id);
  if (error) {
    console.error("[profile/crs]", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true, crs_profile_completed: update.crs_profile_completed });
}
