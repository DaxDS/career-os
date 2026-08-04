/**
 * Sync server secrets from .env.server to Vercel production.
 *
 * Previously read backend/.env. That directory held an undeployed parallel
 * implementation and was removed; the secrets file moved to the repo root, where
 * `.env*` keeps it gitignored.
 *
 * Usage:
 *   npm run sync:vercel-secrets
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { syncVercelEnv } from "./vercel-env-sync.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SERVER_ENV = join(ROOT, ".env.server");

const SYNC_KEYS = [
  "ANTHROPIC_API_KEY",
  "STRIPE_SECRET_KEY",
  "STRIPE_PRICE_PRO",
  // One-time report price. Omitted here originally, so a sync would silently leave
  // /api/billing/report-checkout returning 503 in production.
  "STRIPE_PRICE_REPORT",
  "STRIPE_WEBHOOK_SECRET",
  // Required by createAdminClient(); without it the Stripe webhook throws and no
  // purchase is ever recorded.
  "SUPABASE_SERVICE_ROLE_KEY",
];

function loadServerEnv() {
  if (!existsSync(SERVER_ENV)) {
    console.error(".env.server not found at the repo root");
    process.exit(1);
  }
  const values = {};
  for (const line of readFileSync(SERVER_ENV, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

const env = loadServerEnv();
console.log("Syncing secrets to Vercel production…");
for (const key of SYNC_KEYS) {
  syncVercelEnv(key, env[key]);
}
console.log("Done. Redeploy: npx vercel --prod --yes");
