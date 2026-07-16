/** Default demo credentials for public sales demos (see scripts/seed-demo-data.mjs). */
export const DEV_CREDENTIALS = {
  email: "demo@careeros.app",
  password: "careeros-dev-password",
  fullName: "Alex Chen (Demo)",
} as const;

export function isSupabaseConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

export function isDemoAccount(email: string): boolean {
  return email.trim().toLowerCase() === DEV_CREDENTIALS.email;
}
