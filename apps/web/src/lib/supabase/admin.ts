import { createClient } from "@supabase/supabase-js";

/** Service-role client for webhooks and server-only writes. Never expose to browser. */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY required for admin operations");
  }
  return createClient(url, key, { auth: { persistSession: false } });
}
