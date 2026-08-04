/** Default demo credentials for public sales demos (see scripts/seed-demo-data.mjs). */
export const DEV_CREDENTIALS = {
  email: "demo@careeros.app",
  password: "careeros-dev-password",
  fullName: "Alex Chen (Demo)",
} as const;

/**
 * Whether to show and pre-fill the shared demo account on the auth pages.
 *
 * Defaults to OFF. These pages previously rendered the demo email and password in a
 * banner and pre-filled both fields unconditionally — in production. Any visitor could
 * press "Log in" and land inside a shared account. Opt in explicitly for a demo
 * environment by setting NEXT_PUBLIC_ENABLE_DEMO_LOGIN=true.
 */
export function isDemoLoginEnabled(): boolean {
  return process.env.NEXT_PUBLIC_ENABLE_DEMO_LOGIN === "true";
}

export function isSupabaseConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

export function isDemoAccount(email: string): boolean {
  return email.trim().toLowerCase() === DEV_CREDENTIALS.email;
}
