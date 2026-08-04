/**
 * Comprehensive Ranking System (CRS) scoring.
 *
 * Port of services/agent/lib/crs.py, kept deliberately line-for-line comparable so the
 * two stay in sync. The scoring runs here, inside Next.js, because the Python agent is
 * not deployed anywhere — routing the product's core promise through a service that
 * does not exist is how you ship a signup flow that dead-ends.
 *
 * Grid version: 2026-08-03.
 *
 * Two facts drive the model:
 *
 *  1. Arranged employment is worth 0 points. IRCC removed those points on 2025-03-25.
 *     A job offer never raises a CRS score.
 *  2. Every factor is capped, and the caps differ with an accompanying spouse.
 *
 * Informational only. Not immigration advice.
 */

export const GRID_VERSION = "2026-08-03";

export const MAX_TOTAL = 1200;
const MAX_CORE_WITH_SPOUSE = 460;
const MAX_CORE_WITHOUT_SPOUSE = 500;
const MAX_SPOUSE_FACTORS = 40;
const MAX_TRANSFERABILITY = 100;
const MAX_ADDITIONAL = 600;

export const EDUCATION_ORDER = [
  "none",
  "secondary",
  "one_year_post_secondary",
  "two_year_post_secondary",
  "bachelors_or_three_year",
  "two_or_more_credentials",
  "masters_or_professional",
  "doctoral",
] as const;

export type EducationLevel = (typeof EDUCATION_ORDER)[number];

export const EDUCATION_LABELS: Record<EducationLevel, string> = {
  none: "Less than secondary school",
  secondary: "Secondary school (high school)",
  one_year_post_secondary: "One-year post-secondary credential",
  two_year_post_secondary: "Two-year post-secondary credential",
  bachelors_or_three_year: "Bachelor's degree or three-year credential",
  two_or_more_credentials: "Two or more credentials, one of them three years or longer",
  masters_or_professional: "Master's or professional degree",
  doctoral: "Doctoral degree (PhD)",
};

/** age -> [withoutSpouse, withSpouse] */
const AGE_POINTS: Record<number, [number, number]> = {
  17: [0, 0], 18: [99, 90], 19: [105, 95],
  20: [110, 100], 21: [110, 100], 22: [110, 100], 23: [110, 100], 24: [110, 100],
  25: [110, 100], 26: [110, 100], 27: [110, 100], 28: [110, 100], 29: [110, 100],
  30: [105, 95], 31: [99, 90], 32: [94, 85], 33: [88, 80], 34: [83, 75],
  35: [77, 70], 36: [72, 65], 37: [66, 60], 38: [61, 55], 39: [55, 50],
  40: [50, 45], 41: [39, 35], 42: [28, 25], 43: [17, 15], 44: [6, 5],
};

const EDUCATION_POINTS: Record<EducationLevel, [number, number]> = {
  none: [0, 0],
  secondary: [30, 28],
  one_year_post_secondary: [90, 84],
  two_year_post_secondary: [98, 91],
  bachelors_or_three_year: [120, 112],
  two_or_more_credentials: [128, 119],
  masters_or_professional: [135, 126],
  doctoral: [150, 140],
};

const CANADIAN_EXPERIENCE_POINTS: Record<number, [number, number]> = {
  0: [0, 0], 1: [40, 35], 2: [53, 46], 3: [64, 56], 4: [72, 63], 5: [80, 70],
};

const SPOUSE_EDUCATION_POINTS: Record<EducationLevel, number> = {
  none: 0,
  secondary: 2,
  one_year_post_secondary: 6,
  two_year_post_secondary: 7,
  bachelors_or_three_year: 8,
  two_or_more_credentials: 9,
  masters_or_professional: 10,
  doctoral: 10,
};

const SPOUSE_CANADIAN_EXPERIENCE_POINTS: Record<number, number> = {
  0: 0, 1: 5, 2: 7, 3: 8, 4: 9, 5: 10,
};

function firstLanguagePoints(clb: number, hasSpouse: boolean): number {
  if (clb >= 10) return hasSpouse ? 32 : 34;
  if (clb === 9) return hasSpouse ? 29 : 31;
  if (clb === 8) return hasSpouse ? 22 : 23;
  if (clb === 7) return hasSpouse ? 16 : 17;
  if (clb === 6) return hasSpouse ? 8 : 9;
  if (clb === 5 || clb === 4) return 6;
  return 0;
}

function secondLanguagePoints(clb: number): number {
  if (clb >= 9) return 6;
  if (clb === 7 || clb === 8) return 3;
  if (clb === 5 || clb === 6) return 1;
  return 0;
}

function spouseLanguagePoints(clb: number): number {
  if (clb >= 9) return 5;
  if (clb === 7 || clb === 8) return 3;
  if (clb === 5 || clb === 6) return 1;
  return 0;
}

export interface LanguageScores {
  reading: number;
  writing: number;
  listening: number;
  speaking: number;
}

export const ZERO_LANGUAGE: LanguageScores = {
  reading: 0, writing: 0, listening: 0, speaking: 0,
};

function abilities(l: LanguageScores): number[] {
  return [l.reading, l.writing, l.listening, l.speaking];
}

export function minAbility(l: LanguageScores): number {
  return Math.min(...abilities(l));
}

export interface SpouseProfile {
  education: EducationLevel;
  firstLanguage: LanguageScores;
  canadianExperienceYears: number;
}

export interface CrsProfile {
  age: number | null;
  education: EducationLevel;
  firstLanguage: LanguageScores;
  secondLanguage: LanguageScores;
  canadianExperienceYears: number;
  foreignExperienceYears: number;
  hasSpouse: boolean;
  spouse: SpouseProfile | null;
  provincialNomination: boolean;
  siblingInCanada: boolean;
  canadianStudyCredential: "one_or_two_year" | "three_year_plus" | null;
  tradesCertificate: boolean;
}

export interface CrsResult {
  total: number;
  core: number;
  spouse: number;
  transferability: number;
  additional: number;
  breakdown: Record<string, number>;
  gridVersion: string;
}

function educationRank(level: EducationLevel): number {
  const i = EDUCATION_ORDER.indexOf(level);
  return i === -1 ? 0 : i;
}

function clampYears(years: number, ceiling: number): number {
  if (!years || years < 0) return 0;
  return Math.min(Math.floor(years), ceiling);
}

export function calculateCrs(p: CrsProfile): CrsResult {
  const spouse = p.hasSpouse;
  const idx = spouse ? 1 : 0;

  // --- core / human capital ---
  let agePoints = 0;
  if (p.age !== null && p.age < 45) agePoints = AGE_POINTS[p.age]?.[idx] ?? 0;

  const educationPoints = (EDUCATION_POINTS[p.education] ?? [0, 0])[idx];

  const firstLang = Math.min(
    abilities(p.firstLanguage).reduce((s, clb) => s + firstLanguagePoints(clb, spouse), 0),
    spouse ? 128 : 136
  );
  const secondLang = Math.min(
    abilities(p.secondLanguage).reduce((s, clb) => s + secondLanguagePoints(clb), 0),
    spouse ? 22 : 24
  );

  const cdnYears = clampYears(p.canadianExperienceYears, 5);
  const cdnExp = CANADIAN_EXPERIENCE_POINTS[cdnYears][idx];

  const coreParts = {
    age: agePoints,
    education: educationPoints,
    first_language: firstLang,
    second_language: secondLang,
    canadian_experience: cdnExp,
  };

  // --- spouse factors ---
  const spouseParts = { spouse_education: 0, spouse_language: 0, spouse_canadian_experience: 0 };
  if (spouse && p.spouse) {
    spouseParts.spouse_education = Math.min(SPOUSE_EDUCATION_POINTS[p.spouse.education] ?? 0, 10);
    spouseParts.spouse_language = Math.min(
      abilities(p.spouse.firstLanguage).reduce((s, clb) => s + spouseLanguagePoints(clb), 0),
      20
    );
    spouseParts.spouse_canadian_experience =
      SPOUSE_CANADIAN_EXPERIENCE_POINTS[clampYears(p.spouse.canadianExperienceYears, 5)];
  }

  // --- skill transferability (each block caps at 50, section caps at 100) ---
  const minFirst = minAbility(p.firstLanguage);
  const strongLanguage = minFirst >= 9;
  const goodLanguage = minFirst >= 7;
  const foreignYears = clampYears(p.foreignExperienceYears, 3);
  const hasPostSecondary = educationRank(p.education) >= EDUCATION_ORDER.indexOf("one_year_post_secondary");
  const advancedCredential = educationRank(p.education) >= EDUCATION_ORDER.indexOf("two_or_more_credentials");

  let eduLang = 0;
  if (hasPostSecondary && goodLanguage) {
    eduLang = strongLanguage ? (advancedCredential ? 50 : 25) : advancedCredential ? 25 : 13;
  }
  let eduExp = 0;
  if (hasPostSecondary && cdnYears >= 1) {
    eduExp = cdnYears >= 2 ? (advancedCredential ? 50 : 25) : advancedCredential ? 25 : 13;
  }
  const educationBlock = Math.min(eduLang + eduExp, 50);

  let foreignLang = 0;
  if (foreignYears >= 1 && goodLanguage) {
    foreignLang = strongLanguage ? (foreignYears >= 3 ? 50 : 25) : foreignYears >= 3 ? 25 : 13;
  }
  let foreignExp = 0;
  if (foreignYears >= 1 && cdnYears >= 1) {
    foreignExp = cdnYears >= 2 ? (foreignYears >= 3 ? 50 : 25) : foreignYears >= 3 ? 25 : 13;
  }
  const foreignBlock = Math.min(foreignLang + foreignExp, 50);

  let tradesBlock = 0;
  if (p.tradesCertificate) {
    if (goodLanguage) tradesBlock = 50;
    else if (minFirst >= 5) tradesBlock = 25;
  }

  const transferability = Math.min(educationBlock + foreignBlock + tradesBlock, MAX_TRANSFERABILITY);

  // --- additional points ---
  let french = 0;
  if (minAbility(p.secondLanguage) >= 7) french = minAbility(p.firstLanguage) >= 5 ? 50 : 25;

  let study = 0;
  if (p.canadianStudyCredential === "three_year_plus") study = 30;
  else if (p.canadianStudyCredential === "one_or_two_year") study = 15;

  const additionalParts = {
    provincial_nomination: p.provincialNomination ? 600 : 0,
    french_bonus: french,
    canadian_study: study,
    sibling_in_canada: p.siblingInCanada ? 15 : 0,
    // Kept explicitly so the zero is visible rather than looking like an omission.
    arranged_employment: 0,
  };

  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);

  const core = Math.min(sum(coreParts), spouse ? MAX_CORE_WITH_SPOUSE : MAX_CORE_WITHOUT_SPOUSE);
  const spouseTotal = Math.min(sum(spouseParts), MAX_SPOUSE_FACTORS);
  const additional = Math.min(sum(additionalParts), MAX_ADDITIONAL);
  const total = Math.min(core + spouseTotal + transferability + additional, MAX_TOTAL);

  return {
    total,
    core,
    spouse: spouseTotal,
    transferability,
    additional,
    breakdown: {
      ...coreParts,
      ...spouseParts,
      education_transferability: educationBlock,
      foreign_experience_transferability: foreignBlock,
      trades_transferability: tradesBlock,
      ...additionalParts,
    },
    gridVersion: GRID_VERSION,
  };
}

/** Age in whole years at a reference date. */
export function ageFrom(dateOfBirth: string | null, on: Date = new Date()): number | null {
  if (!dateOfBirth) return null;
  const dob = new Date(`${dateOfBirth.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(dob.getTime())) return null;
  let age = on.getUTCFullYear() - dob.getUTCFullYear();
  const monthDiff = on.getUTCMonth() - dob.getUTCMonth();
  if (monthDiff < 0 || (monthDiff === 0 && on.getUTCDate() < dob.getUTCDate())) age -= 1;
  return age >= 0 && age < 130 ? age : null;
}
