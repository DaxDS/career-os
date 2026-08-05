import type { SupabaseClient } from "@supabase/supabase-js";
import { buildBaseResume } from "@/lib/tailoring/build-base-resume";
import { coverLetterWithClaude, isClaudeConfigured, tailorWithClaude } from "@/lib/tailoring/claude-tailor";
import type { BaseResume, TailoredResume } from "@/lib/tailoring/resume-types";
import { createAdminClient } from "@/lib/supabase/admin";

type ProfileRow = {
  full_name: string | null;
  status: string | null;
  city: string | null;
  province: string | null;
};

type JobRow = {
  title: string;
  company: string | null;
  city: string | null;
  province: string | null;
  noc_code: string | null;
  teer_level: number | null;
  url: string | null;
  parsed_requirements?: Record<string, unknown> | null;
  raw_jd?: string | null;
};

export type PrepareResult = {
  application_id: string;
  pdf_generated: boolean;
  status: "pending_review";
};

function templateTailor(base: BaseResume, job: JobRow): TailoredResume {
  const noc = job.noc_code || "NOC";
  const hasExperience = base.experience.length > 0;

  // Both claims below previously asserted regardless of whether there was any
  // recorded experience to back them — see buildBaseResume for the matching fix on
  // the fabricated-job side of this same problem.
  const summary = hasExperience
    ? `${base.full_name} targets ${job.title} roles (NOC ${noc}, TEER ${job.teer_level ?? "—"}), with experience relevant to the published pathway criteria for this occupation.`
    : `${base.full_name} is targeting ${job.title} roles (NOC ${noc}, TEER ${job.teer_level ?? "—"}) in Canada.`;

  const changes_made = [{ section: "summary", reason: `Refocused summary for ${job.title} at ${job.company}.` }];
  if (hasExperience) {
    changes_made.push({
      section: "experience",
      reason: `Highlighted duties aligned to NOC ${noc} requirements.`,
    });
  }

  return { ...base, summary, changes_made };
}

function templateCoverLetter(profile: ProfileRow, job: JobRow): string {
  const name = profile.full_name || "Applicant";

  // Previously claimed "recent Canadian experience maps to NOC X" and "no LMIA
  // needed for this role" unconditionally, for every applicant and every job. The
  // first is unverifiable from what the tailoring pipeline actually knows; the
  // second requires per-job authorization data (jobs.lmia_flag /
  // work_auth_required) that the discovery pipeline never populates — asserting it
  // was a guess dressed as a fact in a document going to a real employer. Both are
  // now stated only when there is something real to point to.
  const statusLine = profile.status
    ? ` I hold ${profile.status.replace(/_/g, " ")} status in Canada.`
    : "";

  return [
    "Dear Hiring Manager,",
    "",
    `I am applying for the ${job.title} position at ${job.company} in ${job.city}, ${job.province}.${statusLine}`,
    "",
    `I am interested in ${job.company}'s work and believe my background fits the TEER ${job.teer_level ?? "1"} requirements listed in the posting. I would welcome the opportunity to discuss how I can contribute to your team.`,
    "",
    "Sincerely,",
    name,
  ].join("\n");
}

async function logActivity(
  userId: string,
  action: string,
  summary: string,
  metadata: Record<string, unknown>
) {
  try {
    const admin = createAdminClient();
    await admin.from("activity_log").insert({
      user_id: userId,
      action,
      summary,
      metadata,
    });
  } catch {
    /* best-effort */
  }
}

async function loadBaseResume(
  supabase: SupabaseClient,
  userId: string,
  profile: ProfileRow
): Promise<BaseResume> {
  const { data: resumeRow } = await supabase
    .from("resumes")
    .select("base_resume_json")
    .eq("user_id", userId)
    .eq("is_primary", true)
    .limit(1)
    .maybeSingle();

  if (resumeRow?.base_resume_json && typeof resumeRow.base_resume_json === "object") {
    return resumeRow.base_resume_json as BaseResume;
  }

  const { data: workHistory } = await supabase
    .from("work_history")
    .select(
      "title, employer, country, province, start_date, end_date, is_current, duties_text, mapped_noc_code, sort_order"
    )
    .eq("user_id", userId)
    .order("sort_order");

  return buildBaseResume(profile, workHistory || []);
}

export async function prepareApplicationLocally(
  supabase: SupabaseClient,
  userId: string,
  matchId: string
): Promise<PrepareResult> {
  const { data: match, error: matchError } = await supabase
    .from("matches")
    .select("*, jobs(*)")
    .eq("id", matchId)
    .eq("user_id", userId)
    .single();

  if (matchError || !match) {
    throw new Error("Match not found");
  }

  const job = match.jobs as JobRow;
  const jobTitle = job.title || "role";
  const useClaude = isClaudeConfigured();
  const mode = useClaude ? "claude" : "template";

  await logActivity(userId, "tailoring_started", `Tailoring resume for ${jobTitle}`, {
    match_id: matchId,
    job_title: jobTitle,
    company: job.company,
    mode,
  });

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, status, city, province")
    .eq("id", userId)
    .single();

  const profileRow: ProfileRow = profile ?? {
    full_name: null,
    status: null,
    city: null,
    province: null,
  };

  const base = await loadBaseResume(supabase, userId, profileRow);

  let tailored: TailoredResume;
  let coverLetter: string;

  if (useClaude) {
    // Each call falls back independently. The two calls were previously in one try
    // block, so a transient failure on the second (cheaper, cover-letter) call
    // discarded a perfectly good result from the first — downgrading both to
    // templates because of a fault in one.
    try {
      tailored = await tailorWithClaude(base, job, profileRow);
    } catch {
      tailored = templateTailor(base, job);
    }
    try {
      const letter = await coverLetterWithClaude(tailored, job, profileRow);
      coverLetter = letter.full_text;
    } catch {
      coverLetter = templateCoverLetter(profileRow, job);
    }
  } else {
    tailored = templateTailor(base, job);
    coverLetter = templateCoverLetter(profileRow, job);
  }

  const appRow = {
    match_id: matchId,
    user_id: userId,
    tailored_resume_json: {
      ...tailored,
      _base_resume: base,
    },
    tailored_resume_pdf_path: null,
    cover_letter_text: coverLetter,
    submission_method: job.url,
    status: "pending_review" as const,
  };

  const { data: existing } = await supabase
    .from("applications")
    .select("id")
    .eq("match_id", matchId)
    .eq("user_id", userId)
    .maybeSingle();

  let applicationId: string;
  if (existing?.id) {
    const { error } = await supabase.from("applications").update(appRow).eq("id", existing.id);
    if (error) throw new Error(error.message);
    applicationId = existing.id;
  } else {
    const { data: inserted, error } = await supabase.from("applications").insert(appRow).select("id").single();
    if (error) throw new Error(error.message);
    applicationId = inserted.id;
  }

  await supabase.from("matches").update({ status: "queued" }).eq("id", matchId);

  await logActivity(
    userId,
    "tailoring_completed",
    `Tailored resume for ${jobTitle} — ready for your review`,
    {
      match_id: matchId,
      application_id: applicationId,
      job_title: jobTitle,
      pdf: false,
      mode,
    }
  );

  return { application_id: applicationId, pdf_generated: false, status: "pending_review" };
}

export function shouldCallAgentService(): boolean {
  const agentUrl = process.env.AGENT_SERVICE_URL;
  if (!agentUrl) return false;
  if (process.env.VERCEL && /localhost|127\.0\.0\.1/.test(agentUrl)) return false;
  return true;
}
