import {
  FREE_TAILORED_MONTHLY_LIMIT,
  normalizePlan,
  type PlanTier,
} from "@careeros/shared";

export function monthStartIso(): string {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)).toISOString();
}

export interface TailoringLimitResult {
  allowed: boolean;
  plan: PlanTier;
  used: number;
  limit: number | null;
  message?: string;
}

export function tailoringLimitResponse(
  plan: PlanTier,
  used: number
): TailoringLimitResult {
  if (plan === "pro") {
    return { allowed: true, plan, used, limit: null };
  }
  if (used >= FREE_TAILORED_MONTHLY_LIMIT) {
    return {
      allowed: false,
      plan,
      used,
      limit: FREE_TAILORED_MONTHLY_LIMIT,
      message: `Free plan includes ${FREE_TAILORED_MONTHLY_LIMIT} tailored applications per month. Upgrade to Pro for unlimited tailoring.`,
    };
  }
  return { allowed: true, plan, used, limit: FREE_TAILORED_MONTHLY_LIMIT };
}

export { normalizePlan };
