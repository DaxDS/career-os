/**
 * Regression tests for the resume tailoring pipeline.
 *
 * Run: npx tsx scripts/test-tailoring.ts (from apps/web)
 *
 * Two things are guarded here:
 *
 * 1. No fabrication. buildBaseResume previously invented a "Software Developer at
 *    Canadian employer" job — with fabricated bullets — whenever a user had zero
 *    work-history rows, which onboarding permits (no minimum). That fake job then
 *    flowed into the generated resume as if it were real, and was handed to Claude
 *    labelled "source of truth — do not invent employers or metrics." The template
 *    cover letter separately asserted "recent Canadian experience" and "no LMIA
 *    needed" unconditionally, for every applicant, regardless of whether either was
 *    true. All three are load-bearing regressions to catch.
 *
 * 2. JSON extraction from LLM output is robust to realistic response shapes —
 *    markdown code fences, leading/trailing prose, and genuinely malformed output —
 *    since that response becomes a document a real employer receives.
 */
import { buildBaseResume } from "../src/lib/tailoring/build-base-resume";
import { extractJsonObject, normalizeTailoredResume } from "../src/lib/tailoring/claude-tailor";
import type { BaseResume } from "../src/lib/tailoring/resume-types";

let passed = 0;
const failures: string[] = [];

function check(description: string, condition: boolean, detail?: string) {
  if (condition) {
    passed += 1;
  } else {
    failures.push(`${description}${detail ? ` — ${detail}` : ""}`);
  }
}

// --- buildBaseResume: no fabrication ---------------------------------------

const emptyHistoryResume = buildBaseResume(
  { full_name: "Jordan Lee", status: "pgwp", city: "Toronto", province: "ON" },
  []
);
check(
  "empty work history produces empty experience array",
  Array.isArray(emptyHistoryResume.experience) && emptyHistoryResume.experience.length === 0,
  `got ${JSON.stringify(emptyHistoryResume.experience)}`
);
check(
  "no fabricated employer name anywhere in output",
  !JSON.stringify(emptyHistoryResume).includes("Canadian employer"),
  JSON.stringify(emptyHistoryResume)
);
check(
  "no fabricated job title anywhere in output",
  !JSON.stringify(emptyHistoryResume).includes("Built and maintained web applications"),
  JSON.stringify(emptyHistoryResume)
);

const realHistoryResume = buildBaseResume(
  { full_name: "Jordan Lee", status: "pgwp", city: "Toronto", province: "ON" },
  [
    {
      title: "Service Desk Analyst",
      employer: "Acme Corp",
      country: "CA",
      province: "ON",
      start_date: "2023-01-01",
      end_date: null,
      is_current: true,
      duties_text: "Resolved tier-1 tickets.\nEscalated hardware issues.",
      mapped_noc_code: "22221",
      sort_order: 0,
    },
  ]
);
check(
  "real work history is preserved, not discarded",
  realHistoryResume.experience.length === 1 && realHistoryResume.experience[0].employer === "Acme Corp",
  JSON.stringify(realHistoryResume.experience)
);

// --- extractJsonObject: robustness -----------------------------------------

const validCases: Array<[string, string]> = [
  ['{"a":1}', "bare JSON"],
  ['Here is the resume:\n```json\n{"a":1}\n```\nLet me know if changes are needed.', "markdown-fenced with prose around it"],
  ['{"a":1,"b":"contains a brace } inside a string"}', "brace character inside a string value"],
  ['  \n{"a":1}\n  ', "surrounding whitespace"],
];

for (const [input, description] of validCases) {
  try {
    const result = extractJsonObject(input) as Record<string, unknown>;
    check(`extractJsonObject parses: ${description}`, result.a === 1, `got ${JSON.stringify(result)}`);
  } catch (e) {
    check(`extractJsonObject parses: ${description}`, false, `threw ${(e as Error).message}`);
  }
}

const invalidCases: Array<[string, string]> = [
  ["I cannot complete this request.", "prose with no JSON at all"],
  ["", "empty response"],
  ["{not valid json", "unterminated object"],
];

for (const [input, description] of invalidCases) {
  let threw = false;
  try {
    extractJsonObject(input);
  } catch {
    threw = true;
  }
  check(`extractJsonObject throws on: ${description}`, threw);
}

// --- normalizeTailoredResume: falls back to base on missing fields ---------

const base: BaseResume = {
  full_name: "Jordan Lee",
  summary: "Base summary",
  experience: [{ title: "Analyst", employer: "Acme", bullets: ["Did things."] }],
};

const normalized = normalizeTailoredResume({ summary: "New summary" }, base);
check(
  "normalizeTailoredResume falls back to base.experience when Claude omits it",
  normalized.experience === base.experience,
  JSON.stringify(normalized.experience)
);
check(
  "normalizeTailoredResume uses the provided summary when present",
  normalized.summary === "New summary"
);

// The dangerous case: base has no real experience, but the model ignored the prompt
// instruction and returned a fabricated job anyway. The code-level backstop must
// still produce an empty array — this cannot depend on the model having complied.
const hallucinatedAgainstEmptyBase = normalizeTailoredResume(
  {
    summary: "Entry-level summary",
    experience: [{ title: "Software Developer", employer: "Canadian employer", bullets: ["Invented."] }],
  },
  { ...base, experience: [] }
);
check(
  "fabricated experience from the model is discarded when the base had none",
  Array.isArray(hallucinatedAgainstEmptyBase.experience) && hallucinatedAgainstEmptyBase.experience.length === 0,
  `got ${JSON.stringify(hallucinatedAgainstEmptyBase.experience)} — the model's output must not override a known-empty base`
);

// --- report ------------------------------------------------------------------

for (const failure of failures) console.error(`FAIL ${failure}`);
console.log(`tailoring: ${passed}/${passed + failures.length} passed`);
if (failures.length > 0) process.exit(1);
