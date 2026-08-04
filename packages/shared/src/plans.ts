export type PlanTier = "free" | "pro";

export interface PlanDefinition {
  label: string;
  priceMonthlyCad: number;
  dailySendCap: number;
  /** null = unlimited (Pro) */
  tailoredApplicationsPerMonth: number | null;
  features: string[];
}

export const PLANS: Record<PlanTier, PlanDefinition> = {
  free: {
    label: "Free",
    priceMonthlyCad: 0,
    dailySendCap: 5,
    tailoredApplicationsPerMonth: 10,
    features: [
      "Your CRS score with full component breakdown",
      "Every Express Entry route currently being drawn, with your gap to each",
      "Ranked next moves, with the points each is worth",
      "Dormant categories flagged so you don't chase closed doors",
    ],
  },
  pro: {
    label: "Pro",
    priceMonthlyCad: 24,
    dailySendCap: 25,
    tailoredApplicationsPerMonth: null,
    features: [
      "Unlimited jobs feed",
      "25 application sends per day",
      "Unlimited tailored applications",
      "Full pathway report refresh",
      "Gmail outreach drafts (you send)",
      "Wage negotiation vs regional median data",
    ],
  },
};

export const FREE_TAILORED_MONTHLY_LIMIT = 10;

export function normalizePlan(tier: string | null | undefined): PlanTier {
  return tier === "pro" ? "pro" : "free";
}
