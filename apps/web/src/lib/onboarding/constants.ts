export const ONBOARDING_STEPS = [
  { id: 0, key: "resume", path: "/onboarding" },
  { id: 1, key: "workHistory", path: "/onboarding/work-history" },
  { id: 2, key: "nocMapping", path: "/onboarding/noc-mapping" },
  { id: 3, key: "permitStatus", path: "/onboarding/permit-status" },
  { id: 4, key: "languages", path: "/onboarding/languages" },
] as const;

export type OnboardingStepId = (typeof ONBOARDING_STEPS)[number]["id"];

export const IMMIGRATION_STATUS_OPTIONS = [
  { value: "citizen", label: "Canadian citizen" },
  { value: "pr", label: "Permanent resident" },
  { value: "pgwp", label: "PGWP holder" },
  { value: "closed_permit", label: "Closed work permit" },
  { value: "open_permit", label: "Open work permit" },
  { value: "outside_canada", label: "Outside Canada (planning to move)" },
] as const;

export const LANGUAGE_PROFICIENCY_OPTIONS = [
  { value: "none", label: "None" },
  { value: "basic", label: "Basic" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
  { value: "native", label: "Native / bilingual" },
] as const;

export const CANADIAN_PROVINCES = [
  "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT",
] as const;
