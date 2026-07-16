"use client";

import { useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { getAuthCallbackUrl } from "@/lib/app-url";
import { DEV_CREDENTIALS, isSupabaseConfigured } from "@/lib/dev-credentials";
import { DevCredentialsHint } from "@/components/auth/dev-credentials-hint";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const t = useTranslations("auth");
  const ta = useTranslations("auth.dev");
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") ?? "/dashboard";
  const configError = searchParams.get("error");
  const [email, setEmail] = useState<string>(DEV_CREDENTIALS.email);
  const [password, setPassword] = useState<string>(DEV_CREDENTIALS.password);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const supabaseConfigured = isSupabaseConfigured();

  async function handleEmailLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!supabaseConfigured) {
      setError(ta("notConfigured"));
      setLoading(false);
      return;
    }

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    router.push(redirect);
    router.refresh();
  }

  async function handleGoogleLogin() {
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
        redirectTo: getAuthCallbackUrl(redirect),
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
          <CardTitle>{t("loginTitle")}</CardTitle>
          <CardDescription>{t("loginDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <DevCredentialsHint label={ta("hint")} />

          {!supabaseConfigured && (
            <p className="text-sm text-destructive">
              {configError === "supabase_not_configured" ? ta("notConfigured") : ta("notConfigured")}
            </p>
          )}

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={handleGoogleLogin}
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

          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t("email")}</Label>
              <Input
                id="email"
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
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading || !supabaseConfigured}>
              {loading ? t("signingIn") : t("login")}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            {t("noAccount")}{" "}
            <Link href="/signup" className="text-primary hover:underline">
              {t("signup")}
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
