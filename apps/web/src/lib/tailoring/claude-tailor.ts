import Anthropic from "@anthropic-ai/sdk";
import type { BaseResume, CoverLetterResult, TailoredResume } from "@/lib/tailoring/resume-types";

const CANADIAN_TAILORING_RULES = `
HARD RULES — Canadian resume norms:
- NO photo, age, marital status, SIN, or references section
- 1–2 pages maximum; reverse-chronological experience
- Canadian spelling (colour, organisation, centre)
- Never fabricate experience, skills, employers, or metrics
- Quantify ONLY with numbers already in the profile
- Ban AI-sounding words: spearheaded, leveraged, passionate, dynamic, synergy, cutting-edge
- Avoid em-dash-heavy cadence; write like a human professional
- No "References available upon request"
`;

const MODEL = process.env.CLAUDE_SONNET_MODEL || "claude-sonnet-4-20250514";

export function isClaudeConfigured(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY?.trim());
}

function getClient(): Anthropic {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error("ANTHROPIC_API_KEY is not configured");
  return new Anthropic({ apiKey: key });
}

// Exported for direct regression testing — parsing LLM output is the most fragile
// part of this pipeline and deserves tests independent of a live API call.
export function extractJsonObject(raw: string): unknown {
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}") + 1;
  if (start === -1 || end <= start) {
    throw new Error("Claude response did not contain JSON");
  }
  return JSON.parse(raw.slice(start, end));
}

export function normalizeTailoredResume(data: unknown, base: BaseResume): TailoredResume {
  const parsed = data as Partial<TailoredResume>;

  // If the base resume has no real work history, the model is told in the prompt not
  // to invent any — but a prompt instruction is not an enforcement mechanism, and
  // models do not always comply. This is the code-level backstop: when we
  // independently know there is no real experience, no amount of confident-looking
  // output from the model is allowed to introduce any. The prompt reduces how often
  // this path is needed; it does not replace it.
  const experience =
    base.experience.length === 0
      ? []
      : Array.isArray(parsed.experience) && parsed.experience.length > 0
        ? parsed.experience
        : base.experience;

  return {
    full_name: parsed.full_name || base.full_name,
    contact: parsed.contact ?? base.contact,
    summary: parsed.summary || base.summary,
    experience,
    education: parsed.education ?? base.education,
    skills: parsed.skills ?? base.skills,
    changes_made: Array.isArray(parsed.changes_made) ? parsed.changes_made : [],
  };
}

type JobContext = {
  title: string;
  company: string | null;
  city: string | null;
  province: string | null;
  noc_code: string | null;
  teer_level: number | null;
  parsed_requirements?: Record<string, unknown> | null;
  raw_jd?: string | null;
};

type ProfileContext = {
  full_name: string | null;
  status: string | null;
};

export async function tailorWithClaude(
  base: BaseResume,
  job: JobContext,
  profile: ProfileContext
): Promise<TailoredResume> {
  const client = getClient();
  const parsed = (job.parsed_requirements || {}) as {
    requirements?: string[];
    skills?: string[];
  };

  const experienceInstruction =
    base.experience.length === 0
      ? "The base resume has NO work experience entries. Do not invent any — leave the experience array empty. Write the summary and skills from education and stated skills only. A fabricated job here is resume fraud committed on this person's behalf."
      : "Rewrite bullets to emphasize skills relevant to this posting. Do not add roles, employers, or bullets beyond what is listed below.";

  const prompt = `Tailor this resume for the job below. Return ONLY valid JSON with fields:
full_name, contact, summary, experience (array of {title, employer, dates, location, bullets}), education, skills, changes_made (array of {section, reason}).

Job: ${job.title} at ${job.company}
Location: ${job.city}, ${job.province}
NOC: ${job.noc_code} TEER ${job.teer_level}
Requirements: ${JSON.stringify((parsed.requirements || []).slice(0, 8))}
Skills sought: ${JSON.stringify(parsed.skills || [])}

Base resume (source of truth — do not invent employers, roles, or metrics beyond this):
${JSON.stringify(base, null, 2).slice(0, 8000)}

Candidate status in Canada: ${profile.status || "work permit holder"}

${experienceInstruction} Do not prepend labels like "Tailored for". Document each meaningful edit in changes_made.`;

  const message = await client.messages.create({
    model: MODEL,
    max_tokens: 4096,
    system: `${CANADIAN_TAILORING_RULES}\nReturn JSON only.`,
    messages: [{ role: "user", content: prompt }],
  });

  const raw = message.content[0]?.type === "text" ? message.content[0].text : "{}";
  return normalizeTailoredResume(extractJsonObject(raw), base);
}

/**
 * Builds the cover-letter prompt. Pure and exported so its content can be tested
 * directly — prompt wording is where the fabrication risk actually lives, and
 * reading it by eye is exactly how the LMIA-exemption instruction below survived one
 * full audit pass before being caught on a second, closer read.
 *
 * Two fabrication risks fixed here, both the Claude-path counterpart of what was
 * already found and fixed in local-prepare.ts's templateCoverLetter:
 *
 * 1. The previous wording — "plausible detail... do not invent press releases" —
 *    forbade exactly one kind of invention while implicitly inviting any other kind
 *    that merely sounded credible. Restricted to only what the JD excerpt actually
 *    contains.
 * 2. The previous wording — "mention they do not require LMIA... if appropriate" —
 *    asked the model to judge LMIA exemption with no real signal to judge it from.
 *    jobs.lmia_flag and work_auth_required exist as columns but the discovery
 *    pipeline never populates either, so "appropriate" had nothing behind it but the
 *    model's own confidence. Replaced with the applicant's own self-reported status
 *    only, exactly as the template path was fixed.
 */
export function buildCoverLetterPrompt(
  tailored: Pick<TailoredResume, "summary" | "experience">,
  job: JobContext,
  profile: ProfileContext
): string {
  const company = job.company || "the company";
  const jdExcerpt = (job.raw_jd || "").slice(0, 2000);
  const keyExperience = tailored.experience.slice(0, 2);

  const specificDetailInstruction = jdExcerpt
    ? `You may reference one detail actually present in the JD excerpt below (sector, location, team focus) if it helps. Do not invent anything about ${company} that is not stated in that excerpt.`
    : `No real detail about ${company} is available beyond its name and location — do not invent one. Keep the letter general rather than fabricating specifics.`;

  const experienceInstruction =
    keyExperience.length === 0
      ? "The candidate has no recorded work experience yet. Do not invent any — write from their education, skills, and interest in the role instead."
      : "";

  const statusInstruction = profile.status
    ? `The applicant holds ${profile.status.replace(/_/g, " ")} status in Canada — you may state this fact only. Do not make any claim about LMIA requirements or work-authorization exemptions for this specific job; that has not been verified.`
    : "";

  return `Write a cover letter ≤250 words for this Canadian job application.
${specificDetailInstruction}
${experienceInstruction}
${CANADIAN_TAILORING_RULES}

Job: ${job.title} at ${company}
Location: ${job.city}, ${job.province}
NOC: ${job.noc_code}
JD excerpt: ${jdExcerpt || `${job.title} role in ${job.city}, ${job.province}.`}
Resume summary: ${tailored.summary}
Key experience: ${JSON.stringify(keyExperience)}
Applicant name: ${profile.full_name || "Applicant"}
${statusInstruction}

Return JSON: {"full_text": "...", "word_count": N}`;
}

export async function coverLetterWithClaude(
  tailored: TailoredResume,
  job: JobContext,
  profile: ProfileContext
): Promise<CoverLetterResult> {
  const client = getClient();
  const prompt = buildCoverLetterPrompt(tailored, job, profile);

  const message = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    system: "Return JSON only. Max 250 words in full_text.",
    messages: [{ role: "user", content: prompt }],
  });

  const raw = message.content[0]?.type === "text" ? message.content[0].text : "{}";
  const data = extractJsonObject(raw) as CoverLetterResult;
  const words = (data.full_text || "").split(/\s+/).filter(Boolean);
  if (words.length > 250) {
    const trimmed = words.slice(0, 250).join(" ");
    return { full_text: trimmed, word_count: 250 };
  }
  return {
    full_text: data.full_text || "",
    word_count: data.word_count || words.length,
  };
}
