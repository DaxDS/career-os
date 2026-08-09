/**
 * Language test score to CLB / NCLC conversion.
 *
 * Transcribed from IRCC's published equivalency charts, verified 2026-08-08:
 * https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/
 * express-entry/documents/language-requirements/language-testing.html
 *
 * The CRS form previously demanded CLB levels directly. Almost nobody knows their CLB —
 * they have an IELTS report saying "7.5 Listening" or a CELPIP score of 9. IRCC's own
 * calculator asks for raw test results and converts internally, so asking for CLB put
 * the burden of a lookup on the user and invited transcription errors in the single
 * largest factor in the score after age.
 *
 * Each table maps a CLB/NCLC level to the MINIMUM score required in each ability. A
 * score is converted by walking from the highest level down and taking the first level
 * whose threshold it meets.
 */

export type Ability = "reading" | "writing" | "listening" | "speaking";

export type EnglishTest = "clb" | "celpip" | "ielts" | "pte";
export type FrenchTest = "none" | "nclc" | "tef" | "tcf";

interface Thresholds {
  level: number;
  speaking: number;
  listening: number;
  reading: number;
  writing: number;
}

/** IELTS General Training — minimum band per ability. */
const IELTS: Thresholds[] = [
  { level: 10, speaking: 7.5, listening: 8.5, reading: 8.0, writing: 7.5 },
  { level: 9, speaking: 7.0, listening: 8.0, reading: 7.0, writing: 7.0 },
  { level: 8, speaking: 6.5, listening: 7.5, reading: 6.5, writing: 6.5 },
  { level: 7, speaking: 6.0, listening: 6.0, reading: 6.0, writing: 6.0 },
  { level: 6, speaking: 5.5, listening: 5.5, reading: 5.0, writing: 5.5 },
  { level: 5, speaking: 5.0, listening: 5.0, reading: 4.0, writing: 5.0 },
  { level: 4, speaking: 4.0, listening: 4.5, reading: 3.5, writing: 4.0 },
];

/** PTE Core — minimum scaled score per ability. */
const PTE: Thresholds[] = [
  { level: 10, speaking: 89, listening: 89, reading: 88, writing: 90 },
  { level: 9, speaking: 84, listening: 82, reading: 78, writing: 88 },
  { level: 8, speaking: 76, listening: 71, reading: 69, writing: 79 },
  { level: 7, speaking: 68, listening: 60, reading: 60, writing: 69 },
  { level: 6, speaking: 59, listening: 50, reading: 51, writing: 60 },
  { level: 5, speaking: 51, listening: 39, reading: 42, writing: 51 },
  { level: 4, speaking: 42, listening: 28, reading: 33, writing: 41 },
];

/** TEF Canada — minimum score per ability. */
const TEF: Thresholds[] = [
  { level: 10, speaking: 393, listening: 316, reading: 263, writing: 393 },
  { level: 9, speaking: 371, listening: 298, reading: 248, writing: 371 },
  { level: 8, speaking: 349, listening: 280, reading: 233, writing: 349 },
  { level: 7, speaking: 310, listening: 249, reading: 207, writing: 310 },
  { level: 6, speaking: 271, listening: 217, reading: 181, writing: 271 },
  { level: 5, speaking: 226, listening: 181, reading: 151, writing: 226 },
  { level: 4, speaking: 181, listening: 145, reading: 121, writing: 181 },
];

/** TCF Canada — speaking and writing are 0-20 scales; listening and reading are 0-699. */
const TCF: Thresholds[] = [
  { level: 10, speaking: 16, listening: 549, reading: 549, writing: 16 },
  { level: 9, speaking: 14, listening: 523, reading: 524, writing: 14 },
  { level: 8, speaking: 12, listening: 503, reading: 499, writing: 12 },
  { level: 7, speaking: 10, listening: 458, reading: 453, writing: 10 },
  { level: 6, speaking: 7, listening: 398, reading: 406, writing: 7 },
  { level: 5, speaking: 6, listening: 369, reading: 375, writing: 6 },
  { level: 4, speaking: 4, listening: 331, reading: 342, writing: 4 },
];

const TABLES: Record<string, Thresholds[]> = { ielts: IELTS, pte: PTE, tef: TEF, tcf: TCF };

/**
 * Convert one ability's raw test score to its CLB/NCLC level.
 *
 * Returns 0 below the lowest published threshold, which is correct for scoring: CRS
 * awards nothing under CLB 4, so there is no reason to distinguish CLB 3 from CLB 0.
 */
export function toClb(test: EnglishTest | FrenchTest, ability: Ability, score: number): number {
  if (!Number.isFinite(score) || score <= 0) return 0;

  // CELPIP levels are already CLB levels; the user's own CLB entry passes straight through.
  if (test === "celpip" || test === "clb" || test === "nclc") {
    return Math.max(0, Math.min(12, Math.round(score)));
  }

  const table = TABLES[test];
  if (!table) return 0;

  for (const row of table) {
    if (score >= row[ability]) return row.level;
  }
  return 0;
}

export interface AbilityScores {
  reading: number;
  writing: number;
  listening: number;
  speaking: number;
}

export function convertAll(
  test: EnglishTest | FrenchTest,
  scores: AbilityScores
): AbilityScores {
  return {
    reading: toClb(test, "reading", scores.reading),
    writing: toClb(test, "writing", scores.writing),
    listening: toClb(test, "listening", scores.listening),
    speaking: toClb(test, "speaking", scores.speaking),
  };
}

/** Input affordances so the form can validate and label each test correctly. */
export const TEST_META: Record<
  EnglishTest | FrenchTest,
  { label: string; min: number; max: number; step: number; hint: string } | null
> = {
  none: null,
  clb: { label: "I already know my CLB levels", min: 0, max: 12, step: 1, hint: "CLB 0-12" },
  nclc: { label: "I already know my NCLC levels", min: 0, max: 12, step: 1, hint: "NCLC 0-12" },
  celpip: { label: "CELPIP-General", min: 0, max: 12, step: 1, hint: "CELPIP level 0-12" },
  ielts: { label: "IELTS General Training", min: 0, max: 9, step: 0.5, hint: "Band 0-9" },
  pte: { label: "PTE Core", min: 0, max: 90, step: 1, hint: "Score 0-90" },
  tef: { label: "TEF Canada", min: 0, max: 450, step: 1, hint: "Score per ability" },
  tcf: {
    label: "TCF Canada",
    min: 0,
    max: 699,
    step: 1,
    hint: "Speaking/writing 0-20, listening/reading 0-699",
  },
};
