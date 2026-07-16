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

function extractJsonObject(raw: string): unknown {
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}") + 1;
  if (start === -1 || end <= start) {
    throw new Error("Claude response did not contain JSON");
  }
  return JSON.parse(raw.slice(start, end));
}

function normalizeTailoredResume(data: unknown, base: BaseResume): TailoredResume {
  const parsed = data as Partial<TailoredResume>;
  return {
    full_name: parsed.full_name || base.full_name,
    contact: parsed.contact ?? base.contact,
    summary: parsed.summary || base.summary,
    experience: Array.isArray(parsed.experience) && parsed.experience.length > 0 ? parsed.experience : base.experience,
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

  const prompt = `Tailor this resume for the job below. Return ONLY valid JSON with fields:
full_name, contact, summary, experience (array of {title, employer, dates, location, bullets}), education, skills, changes_made (array of {section, reason}).

Job: ${job.title} at ${job.company}
Location: ${job.city}, ${job.province}
NOC: ${job.noc_code} TEER ${job.teer_level}
Requirements: ${JSON.stringify((parsed.requirements || []).slice(0, 8))}
Skills sought: ${JSON.stringify(parsed.skills || [])}

Base resume (source of truth — do not invent employers or metrics):
${JSON.stringify(base, null, 2).slice(0, 8000)}

Candidate status in Canada: ${profile.status || "work permit holder"}

Rewrite bullets to emphasize skills relevant to this posting. Reorder or rephrase; do not prepend labels like "Tailored for". Document each meaningful edit in changes_made.`;

  const message = await client.messages.create({
    model: MODEL,
    max_tokens: 4096,
    system: `${CANADIAN_TAILORING_RULES}\nReturn JSON only.`,
    messages: [{ role: "user", content: prompt }],
  });

  const raw = message.content[0]?.type === "text" ? message.content[0].text : "{}";
  return normalizeTailoredResume(extractJsonObject(raw), base);
}

export async function coverLetterWithClaude(
  tailored: TailoredResume,
  job: JobContext,
  profile: ProfileContext
): Promise<CoverLetterResult> {
  const client = getClient();
  const company = job.company || "the company";
  const jdExcerpt = (job.raw_jd || "").slice(0, 2000);
  const keyExperience = tailored.experience.slice(0, 2);

  const prompt = `Write a cover letter ≤250 words for this Canadian job application.
Reference ONE specific, plausible detail about ${company} or the role (sector, location, or team focus — do not invent press releases).
${CANADIAN_TAILORING_RULES}

Job: ${job.title} at ${company}
Location: ${job.city}, ${job.province}
NOC: ${job.noc_code}
JD excerpt: ${jdExcerpt || `${job.title} role in ${job.city}, ${job.province}.`}
Resume summary: ${tailored.summary}
Key experience: ${JSON.stringify(keyExperience)}
Applicant name: ${profile.full_name || "Applicant"}
Work authorization: ${profile.status || "valid Canadian work permit"} — mention they do not require LMIA for this role if appropriate.

Return JSON: {"full_text": "...", "word_count": N}`;

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
