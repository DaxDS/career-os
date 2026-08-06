"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useTranslations } from "next-intl";
import { SettingsBillingCard } from "@/components/settings/settings-billing-card";
import { ThemeSelector } from "@/components/settings/theme-selector";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [confirmWord, setConfirmWord] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const confirmWordRequired = t("deleteConfirmWord");
  const canDelete = confirmWord.trim().toUpperCase() === confirmWordRequired.toUpperCase();

  async function handleExport() {
    setLoading(true);
    setMessage(null);
    const supabase = createClient();
    const { data, error } = await supabase.rpc("data_export");
    if (error) setMessage(error.message);
    else setExportData(JSON.stringify(data, null, 2));
    setLoading(false);
  }

  function downloadExport() {
    if (!exportData) return;
    // Reading a JSON blob in a <pre> is not a usable export for a data-portability
    // request — this makes it an actual file the user can keep.
    const blob = new Blob([exportData], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `careeros-data-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleDeleteAccount() {
    if (!canDelete) return;
    setDeleting(true);
    setMessage(null);
    const supabase = createClient();
    const { error } = await supabase.rpc("delete_user_account");
    if (error) {
      setMessage(error.message);
      setDeleting(false);
      return;
    }
    window.location.href = "/";
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
          <div className="space-y-2">
            <Button variant="outline" onClick={handleExport} disabled={loading}>
              {t("exportData")}
            </Button>
            <p className="text-xs text-muted-foreground">{t("exportHint")}</p>
          </div>

          {exportData && (
            <div className="space-y-2">
              <Button variant="outline" size="sm" onClick={downloadExport}>
                {t("exportDownload")}
              </Button>
              <pre className="max-h-64 overflow-auto rounded-md bg-muted p-4 text-xs">{exportData}</pre>
            </div>
          )}

          {/* Account deletion is irreversible and cascades across every table plus
              stored resume files. A single browser confirm() is too weak a guard for
              that — one stray click destroyed everything with no undo and no backup. */}
          {!confirmingDelete ? (
            <Button variant="destructive" onClick={() => setConfirmingDelete(true)} disabled={loading}>
              {t("deleteAccount")}
            </Button>
          ) : (
            <div className="space-y-3 rounded-md border border-destructive/40 bg-destructive/5 p-4">
              <p className="font-medium text-destructive">{t("deleteConfirmTitle")}</p>
              <p className="text-sm text-muted-foreground">{t("deleteConfirmBody")}</p>
              <div className="space-y-2">
                <Label htmlFor="delete-confirm">{t("deleteConfirmPrompt")}</Label>
                <Input
                  id="delete-confirm"
                  value={confirmWord}
                  onChange={(e) => setConfirmWord(e.target.value)}
                  autoComplete="off"
                  placeholder={confirmWordRequired}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="destructive" onClick={handleDeleteAccount} disabled={!canDelete || deleting}>
                  {deleting ? t("deleting") : t("deleteConfirmCta")}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setConfirmingDelete(false);
                    setConfirmWord("");
                  }}
                  disabled={deleting}
                >
                  {t("cancel")}
                </Button>
              </div>
            </div>
          )}

          <Button
            variant="ghost"
            onClick={async () => {
              const supabase = createClient();
              await supabase.auth.signOut();
              window.location.href = "/login";
            }}
          >
            {t("signOut")}
          </Button>

          {message && <p className="text-sm text-destructive">{message}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
