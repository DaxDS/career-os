"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useTranslations } from "next-intl";
import { SettingsBillingCard } from "@/components/settings/settings-billing-card";
import { ThemeSelector } from "@/components/settings/theme-selector";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function BillingSection() {
  return (
    <Suspense fallback={<p>…</p>}>
      <SettingsBillingCard />
    </Suspense>
  );
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const [exportData, setExportData] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleExport() {
    setLoading(true);
    setMessage(null);
    const supabase = createClient();
    const { data, error } = await supabase.rpc("data_export");
    if (error) setMessage(error.message);
    else setExportData(JSON.stringify(data, null, 2));
    setLoading(false);
  }

  async function handleDeleteAccount() {
    if (!confirm("Permanently delete your account and all data? This cannot be undone.")) return;
    setLoading(true);
    const supabase = createClient();
    const { error } = await supabase.rpc("delete_user_account");
    if (error) {
      setMessage(error.message);
      setLoading(false);
      return;
    }
    window.location.href = "/";
  }

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    window.location.href = "/login";
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>

      <BillingSection />

      <Card>
        <CardHeader>
          <CardTitle>{t("themeTitle")}</CardTitle>
          <CardDescription>{t("themeDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <ThemeSelector />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("activityTitle")}</CardTitle>
          <CardDescription>{t("activityDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline">
            <Link href="/activity">{t("viewActivity")}</Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("accountTitle")}</CardTitle>
          <CardDescription>{t("accountDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button variant="outline" onClick={handleExport} disabled={loading}>
            {t("exportData")}
          </Button>
          {exportData && (
            <pre className="max-h-64 overflow-auto rounded-md bg-muted p-4 text-xs">{exportData}</pre>
          )}
          <Button variant="destructive" onClick={handleDeleteAccount} disabled={loading}>
            {t("deleteAccount")}
          </Button>
          <Button variant="ghost" onClick={handleSignOut}>
            {t("signOut")}
          </Button>
          {message && <p className="text-sm text-destructive">{message}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
