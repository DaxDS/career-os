/**
 * One-shot Supabase production setup for CareerOS.
 *
 * Requires SUPABASE_ACCESS_TOKEN from https://supabase.com/dashboard/account/tokens
 * Also reads NEXT_PUBLIC_* from apps/web/.env.local when present.
 *
 * Usage:
 *   SUPABASE_ACCESS_TOKEN=sbp_... npm run setup:supabase
 */
import { createClient } from "@supabase/supabase-js";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const MIGRATIONS_DIR = join(ROOT, "supabase", "migrations");

const PROJECT_REF = "nvsxswvdktnphktrrxlg";
const APP_URL = "https://career-os-daxds.vercel.app";
const MANAGEMENT_API = "https://api.supabase.com/v1";

function loadEnvLocal() {
  const path = join(ROOT, "apps", "web", ".env.local");
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

loadEnvLocal();

const accessToken = process.env.SUPABASE_ACCESS_TOKEN;
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || `https://${PROJECT_REF}.supabase.co`;

if (!accessToken) {
  console.error(
    "Missing SUPABASE_ACCESS_TOKEN.\n" +
      "Create one at https://supabase.com/dashboard/account/tokens then run:\n" +
      "  SUPABASE_ACCESS_TOKEN=sbp_... npm run setup:supabase"
  );
  process.exit(1);
}

async function mgmt(path, options = {}) {
  const res = await fetch(`${MANAGEMENT_API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    throw new Error(`Management API ${path} failed (${res.status}): ${text}`);
  }
  return body;
}

async function patchAuthConfig() {
  console.log("Updating Supabase Auth URL config + email confirmation…");
  await mgmt(`/projects/${PROJECT_REF}/config/auth`, {
    method: "PATCH",
    body: JSON.stringify({
      site_url: APP_URL,
      uri_allow_list: `${APP_URL}/**,http://localhost:3000/**`,
      mailer_autoconfirm: true,
    }),
  });
  console.log("  site_url:", APP_URL);
  console.log("  mailer_autoconfirm: true (no email confirmation required)");
}

async function runMigrations() {
  console.log("Applying database migrations…");
  const files = readdirSync(MIGRATIONS_DIR)
    .filter((f) => f.endsWith(".sql"))
    .sort();

  for (const file of files) {
    const query = readFileSync(join(MIGRATIONS_DIR, file), "utf8");
    console.log(`  → ${file}`);
    await mgmt(`/projects/${PROJECT_REF}/database/query`, {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  }
}

async function fetchServiceRoleKey() {
  console.log("Fetching service role key…");
  const keys = await mgmt(`/projects/${PROJECT_REF}/api-keys?reveal=true`);
  const list = Array.isArray(keys) ? keys : keys?.data || [];

  const service =
    list.find((k) => k.name === "service_role") ||
    list.find((k) => k?.api_key?.includes?.("service_role"));

  const serviceKey = service?.api_key || process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!serviceKey) {
    console.warn("  Could not auto-detect service role key; skip user confirm + Vercel sync.");
    return null;
  }
  return serviceKey;
}

async function syncVercelEnv(serviceRoleKey) {
  console.log("Syncing SUPABASE_SERVICE_ROLE_KEY to Vercel production…");
  try {
    execSync(`npx vercel env rm SUPABASE_SERVICE_ROLE_KEY production -y`, {
      cwd: ROOT,
      stdio: "ignore",
      shell: true,
    });
  } catch {
    /* not set yet */
  }
  try {
    execSync(`echo "${serviceRoleKey}" | npx vercel env add SUPABASE_SERVICE_ROLE_KEY production`, {
      cwd: ROOT,
      stdio: "inherit",
      shell: true,
    });
  } catch {
    console.warn("  Vercel env sync failed (run manually if needed).");
  }
}

async function confirmExistingUsers(serviceRoleKey) {
  console.log("Confirming existing auth users…");
  const admin = createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { data, error } = await admin.auth.admin.listUsers({ perPage: 200 });
  if (error) throw error;

  for (const user of data.users) {
    if (user.email_confirmed_at) continue;
    await admin.auth.admin.updateUserById(user.id, { email_confirm: true });
    console.log(`  confirmed ${user.email}`);
  }
}

async function main() {
  await patchAuthConfig();
  await runMigrations();
  const serviceRoleKey = await fetchServiceRoleKey();
  if (serviceRoleKey) {
    await syncVercelEnv(serviceRoleKey);
    await confirmExistingUsers(serviceRoleKey);
  }
  console.log("\nDone. Redeploy Vercel, then sign in at", `${APP_URL}/login`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
