import Stripe from "stripe";

let stripe: Stripe | null = null;

/** Server-only Stripe client — import only from API routes. */
export function getStripe(): Stripe {
  if (!stripe) {
    const key = process.env.STRIPE_SECRET_KEY?.trim();
    if (!key) throw new Error("STRIPE_SECRET_KEY is not configured");
    stripe = new Stripe(key);
  }
  return stripe;
}

export function getAppUrl(): string {
  return process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
}
