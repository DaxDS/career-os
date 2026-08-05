export type ImmigrationStatus =
  | "citizen"
  | "pr"
  | "pgwp"
  | "closed_permit"
  | "open_permit"
  | "outside_canada";

export type LanguageProficiency =
  | "none"
  | "basic"
  | "intermediate"
  | "advanced"
  | "native";

export type MatchStatus = "new" | "queued" | "approved" | "rejected" | "expired";

export type ApplicationStatus =
  | "pending_review"
  | "approved"
  | "sent"
  | "response"
  | "interview"
  | "offer"
  | "rejected";

export type ClearanceLevel = "none" | "reliability" | "secret";

/** Legacy shape — used by marketing fixtures and the seed-demo-data script. */
export interface PathwayFlags {
  ee_eligible?: boolean;
  ee_categories?: string[];
  pnp_streams?: string[];
  aip_relevant?: boolean;
}

/**
 * PR-delta shape — what apps/web/src/lib/jobs/score.ts actually writes to
 * matches.pathway_flags for real, discovery-created rows. Distinct from PathwayFlags
 * because the PR-delta model (CRS points, live categories, CEC gap) isn't a set of
 * yes/no flags — it's a comparison against draw history. Kept as a separate type
 * rather than folded into PathwayFlags so a row's shape says which model produced it.
 */
export interface PrDeltaFlags {
  unlocked_categories?: Array<{ id: string; label: string; itas: number; cutoff: number | null }>;
  dormant_but_eligible?: string[];
  cec_eligible?: boolean;
}

export interface ScoreBreakdown {
  noc_alignment?: number;
  skills_overlap?: number;
  experience_fit?: number;
  location_ok?: number;
  wage_fit?: number;
  gaps?: string[];
  // PR-delta fields — what score.ts actually writes for real, discovery-created
  // matches. See PrDeltaFlags for why this isn't folded into the fields above.
  crsNow?: number;
  crsAfter12Months?: number;
  crsDelta?: number;
  verdict?: string;
}

export * from "./database.types";
export * from "./plans";
