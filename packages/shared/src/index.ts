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

export interface PathwayFlags {
  ee_eligible?: boolean;
  ee_categories?: string[];
  pnp_streams?: string[];
  aip_relevant?: boolean;
}

export interface ScoreBreakdown {
  noc_alignment?: number;
  skills_overlap?: number;
  experience_fit?: number;
  location_ok?: number;
  wage_fit?: number;
  gaps?: string[];
}

export * from "./database.types";
export * from "./plans";
