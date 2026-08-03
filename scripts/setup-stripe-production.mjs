/**
 * Stripe setup for CareerOS.
 *
 * Creates two prices, because the app sells two different things:
 *   - Pro subscription, $24 CAD/month  -> STRIPE_PRICE_PRO   (mode: subscription)
 *   - PR pathway report, $29 CAD once  -> STRIPE_PRICE_REPORT (mode: payment)
 *
 * The report price MUST be one-time. /api/billing/report-checkout opens the session
 * with mode "payment", and Stripe rejects a recurring price in that mode.
 *
 * Test mode (sk_test_...) costs $0 — use card 4242 4242 4242 4242.
 *
 * Usage:
 *   STRIPE_SECRET_KEY=sk_test_... npm run setup:stripe
 *   npm run setup:stripe   # if STRIPE_SECRET_KEY is in .env.server
 */
import { execSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { syncVercelEnv } from "./vercel-env-sync.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const SERVER_ENV = join(ROOT, ".env.server");
const WEB_ENV = join(ROOT, "apps", "web", ".env.local");
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://career-os-daxds.vercel.app";
const WEBHOOK_PATH = "/api/stripe/webhook";
const WEBHOOK_URL = `${APP_URL}${WEBHOOK_PATH}`;
const STRIPE_API = "https://api.stripe.com/v1";

const PRO_LOOKUP_KEY = "careeros_pro_monthly_cad_2400";
const REPORT_LOOKUP_KEY = "careeros_report_onetime_cad_2900";
const REPORT_AMOUNT_CENTS = "2900";

function loadEnvFile(path) {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq);
    let value = trimmed.slice(eq + 1);
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = value;
  }
}

function upsertEnvFile(path, updates) {
  const lines = existsSync(path) ? readFileSync(path, "utf8").split("\n") : [];
  for (const [key, value] of Object.entries(updates)) {
    if (!value) continue;
    const next = `${key}=${value}`;
    const idx = lines.findIndex((line) => line.trim().startsWith(`${key}=`));
    if (idx >= 0) lines[idx] = next;
    else lines.push(next);
  }
  writeFileSync(path, lines.filter((l, i, arr) => i < arr.length - 1 || l.trim()).join("\n") + "\n");
}

loadEnvFile(SERVER_ENV);
loadEnvFile(WEB_ENV);

const secretKey = process.env.STRIPE_SECRET_KEY;
if (!secretKey?.startsWith("sk_")) {
  console.error(
    "Missing STRIPE_SECRET_KEY.\n\n" +
      "Free path (test mode, $0):\n" +
      "  1. Create a free account at https://dashboard.stripe.com/register\n" +
      "  2. Developers → API keys → copy Secret key (starts with sk_test_)\n" +
      "  3. Add to .env.server at the repo root: STRIPE_SECRET_KEY=sk_test_...\n" +
      "  4. Run: npm run setup:stripe\n\n" +
      "Or one-liner:\n" +
      "  STRIPE_SECRET_KEY=sk_test_... npm run setup:stripe"
  );
  process.exit(1);
}

const isTestMode = secretKey.startsWith("sk_test_");
console.log(isTestMode ? "Stripe TEST mode — no real charges." : "Stripe LIVE mode — real payments enabled.");

async function stripeRequest(path, method = "GET", fields = null) {
  const init = {
    method,
    headers: {
      Authorization: `Bearer ${secretKey}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
  };
  if (fields) {
    init.body = new URLSearchParams(fields).toString();
  }
  const res = await fetch(`${STRIPE_API}${path}`, init);
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    throw new Error(`Stripe ${path} failed (${res.status}): ${text}`);
  }
  return body;
}

async function ensureProPrice() {
  if (process.env.STRIPE_PRICE_PRO) {
    console.log("Using existing STRIPE_PRICE_PRO:", process.env.STRIPE_PRICE_PRO);
    return process.env.STRIPE_PRICE_PRO;
  }

  console.log("Creating CareerOS Pro product + $24 CAD/month price…");
  try {
    const existing = await stripeRequest(
      `/prices?lookup_keys[]=${encodeURIComponent(PRO_LOOKUP_KEY)}&limit=1`
    );
    if (existing.data?.[0]?.id) {
      console.log("  Found price via lookup key:", existing.data[0].id);
      return existing.data[0].id;
    }
  } catch {
    /* create below */
  }

  const product = await stripeRequest("/products", "POST", {
    name: "CareerOS Pro",
    description: "Pro plan — unlimited tailoring, 25 sends/day, pathway refresh",
  });

  const price = await stripeRequest("/prices", "POST", {
    product: product.id,
    currency: "cad",
    unit_amount: "2400",
    "recurring[interval]": "month",
    lookup_key: PRO_LOOKUP_KEY,
  });

  console.log("  product:", product.id);
  console.log("  price:", price.id);
  return price.id;
}

async function ensureReportPrice() {
  if (process.env.STRIPE_PRICE_REPORT) {
    console.log("Using existing STRIPE_PRICE_REPORT:", process.env.STRIPE_PRICE_REPORT);
    return process.env.STRIPE_PRICE_REPORT;
  }

  console.log("Creating PR Pathway Report product + $29 CAD one-time price…");
  try {
    const existing = await stripeRequest(
      `/prices?lookup_keys[]=${encodeURIComponent(REPORT_LOOKUP_KEY)}&limit=1`
    );
    if (existing.data?.[0]?.id) {
      console.log("  Found price via lookup key:", existing.data[0].id);
      return existing.data[0].id;
    }
  } catch {
    /* create below */
  }

  const product = await stripeRequest("/products", "POST", {
    name: "CareerOS PR Pathway Report",
    description:
      "One-time report: your CRS score, the Express Entry routes currently being drawn, your gap to each, and ranked next moves.",
  });

  // No recurring[interval] — omitting it is what makes this a one-time price.
  const price = await stripeRequest("/prices", "POST", {
    product: product.id,
    currency: "cad",
    unit_amount: REPORT_AMOUNT_CENTS,
    lookup_key: REPORT_LOOKUP_KEY,
  });

  console.log("  product:", product.id);
  console.log("  price:", price.id);
  return price.id;
}

async function ensureWebhook() {
  if (process.env.STRIPE_WEBHOOK_SECRET) {
    console.log("Using existing STRIPE_WEBHOOK_SECRET");
    return process.env.STRIPE_WEBHOOK_SECRET;
  }

  console.log("Configuring Stripe webhook →", WEBHOOK_URL);
  const listed = await stripeRequest("/webhook_endpoints?limit=100");
  const match = listed.data?.find((ep) => ep.url === WEBHOOK_URL);

  if (match?.id) {
    console.log("  Webhook endpoint exists:", match.id);
    console.warn(
      "  Could not read signing secret for existing endpoint.\n" +
        "  Copy whsec_... from Stripe Dashboard → Developers → Webhooks, or delete and re-run setup."
    );
    return null;
  }

  const created = await stripeRequest("/webhook_endpoints", "POST", {
    url: WEBHOOK_URL,
    "enabled_events[0]": "checkout.session.completed",
    "enabled_events[1]": "customer.subscription.updated",
    "enabled_events[2]": "customer.subscription.deleted",
    description: "CareerOS production billing",
  });

  console.log("  Created webhook:", created.id);
  if (created.secret) {
    console.log("  Webhook signing secret captured.");
    return created.secret;
  }
  return null;
}

async function main() {
  const priceId = await ensureProPrice();
  const reportPriceId = await ensureReportPrice();
  const webhookSecret = await ensureWebhook();

  const localEnv = {
    STRIPE_SECRET_KEY: secretKey,
    STRIPE_PRICE_PRO: priceId,
    STRIPE_PRICE_REPORT: reportPriceId,
  };
  if (webhookSecret) localEnv.STRIPE_WEBHOOK_SECRET = webhookSecret;

  console.log("\nSaving Stripe vars to .env.server and apps/web/.env.local…");
  upsertEnvFile(SERVER_ENV, localEnv);
  upsertEnvFile(WEB_ENV, localEnv);

  syncVercelEnv("STRIPE_SECRET_KEY", secretKey);
  syncVercelEnv("STRIPE_PRICE_PRO", priceId);
  syncVercelEnv("STRIPE_PRICE_REPORT", reportPriceId);
  if (webhookSecret) {
    syncVercelEnv("STRIPE_WEBHOOK_SECRET", webhookSecret);
  }

  console.log("\nStripe setup complete.");
  console.log("  STRIPE_PRICE_PRO:   ", priceId);
  console.log("  STRIPE_PRICE_REPORT:", reportPriceId);
  if (!webhookSecret) {
    console.log("\nNext: add STRIPE_WEBHOOK_SECRET to Vercel manually, then redeploy:");
    console.log("  npx vercel --prod --yes");
  } else {
    console.log("\nRedeploy for env vars to take effect:");
    console.log("  npx vercel --prod --yes");
  }
  if (isTestMode) {
    console.log("\nTest checkout (no charge):");
    console.log("  Card: 4242 4242 4242 4242 · any future expiry · any CVC");
    console.log("  Settings → Upgrade to Pro on https://career-os-daxds.vercel.app");
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
