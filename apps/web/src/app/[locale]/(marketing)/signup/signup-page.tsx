"use client";

import { useState } from "react";
import { Link, useRouter } from "@/i18n/routing";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { getAuthCallbackUrl } from "@/lib/app-url";
import { DEV_CREDENTIALS, isDemoLoginEnabled, isSupabaseConfigured } from "@/lib/dev-credentials";
import { DevCredentialsHint } from "@/components/auth/dev-credentials-hint";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SignupPage() {
  const t = useTranslations("auth");
  const ta = useTranslations("auth.dev");
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan");
  const demoLogin = isDemoLoginEnabled();
  const [email, setEmail] = useState<string>(demoLogin ? DEV_CREDENTIALS.email : "");
  const [password, setPassword] = useState<string>(demoLogin ? DEV_CREDENTIALS.password : "");
  const [fullName, setFullName] = useState<string>(demoLogin ? DEV_CREDENTIALS.fullName : "");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const supabaseConfigured = isSupabaseConfigured();

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    if (!supabaseConfigured) {
      setError(ta("notConfigured"));
      setLoading(false);
      return;
    }

    const supabase = createClient();
    const { data, error: authError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, plan: plan ?? "free" },
        emailRedirectTo: getAuthCallbackUrl("/onboarding"),
      },
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    if (data.session) {
      router.push("/onboarding");
      router.refresh();
      return;
    }

    setMessage(ta("confirmEmail"));
    setLoading(false);
  }

  async function handleGoogleSignup() {
    setLoading(true);
    setError(null);

    if (!supabaseConfigured) {
      setError(ta("notConfigured"));
      setLoading(false);
      return;
    }

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: getAuthCallbackUrl("/onboarding"),
      },
    });
    if (authError) {
      setError(authError.message);
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle as="h1" className="text-2xl">{t("signupTitle")}</CardTitle>
          <CardDescription>{t("signupDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {demoLogin && <DevCredentialsHint label={ta("hint")} />}

          {!supabaseConfigured && (
            <p className="text-sm text-destructive">{ta("notConfigured")}</p>
          )}

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={handleGoogleSignup}
            disabled={loading || !supabaseConfigured}
          >
            {t("continueWithGoogle")}
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">{ta("orEmail")}</span>
            </div>
          </div>

          <form onSubmit={handleSignup} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">{t("fullName")}</Label>
              <Input
                id="fullName"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">{t("email")}</Label>
              <Input
                id="email"
                autoComplete="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t("password")}</Label>
              <Input
                id="password"
                autoComplete="new-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
              {/* Stated up front rather than surfaced as a browser rejection after
                  the user has already committed to a password. */}
              <p className="text-xs text-muted-foreground">{t("passwordHint")}</p>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {message && <p className="text-sm text-emerald-700">{message}</p>}
            <Button type="submit" className="w-full" disabled={loading || !supabaseConfigured}>
              {loading ? t("creatingAccount") : t("signup")}
            </Button>
          </form>

          {/* This form asks for the starting point of someone's immigration profile
              and previously carried no reassurance at all about cost, data residency
              or reversibility. */}
          <p className="text-xs leading-relaxed text-muted-foreground">{t("signupTrust")}</p>

          <p className="text-center text-sm text-muted-foreground">
            {t("hasAccount")}{" "}
            <Link href="/login" className="text-primary hover:underline">
              {t("login")}
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
