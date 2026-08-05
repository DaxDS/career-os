"use client";

import { useRouter } from "@/i18n/routing";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt"];

/** Strip path separators and anything exotic; the storage key is built from this. */
function safeFileName(name: string): string {
  const base = name.split(/[\\/]/).pop() ?? "resume";
  return base.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 120) || "resume";
}

export default function ResumeUploadStep() {
  const t = useTranslations("onboarding.resume");
  const tc = useTranslations("common");
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function pickFile(selected: File | null) {
    setError(null);
    if (!selected) {
      setFile(null);
      return;
    }
    const lower = selected.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
      setError("Upload a PDF, Word document, or plain text file.");
      setFile(null);
      return;
    }
    if (selected.size > MAX_BYTES) {
      setError("That file is larger than 10 MB. Please upload a smaller file.");
      setFile(null);
      return;
    }
    if (selected.size === 0) {
      setError("That file is empty.");
      setFile(null);
      return;
    }
    setFile(selected);
  }

  async function handleContinue() {
    setLoading(true);
    setError(null);

    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      setLoading(false);
      router.push("/login");
      return;
    }

    // Upload is optional. It was previously required to continue, which blocked the
    // entire funnel for anyone without a file to hand — and nothing reads the file
    // yet, so it gated onboarding for no benefit.
    if (file) {
      // A user who goes Back and re-uploads must not end up with two rows both
      // flagged primary — the database enforces at most one now, so this insert
      // would otherwise fail outright on a second upload. Replace, not accumulate:
      // unset and physically delete the previous primary first.
      const { data: previous } = await supabase
        .from("resumes")
        .select("id, storage_path")
        .eq("user_id", user.id)
        .eq("is_primary", true)
        .maybeSingle();

      if (previous) {
        await supabase.from("resumes").update({ is_primary: false }).eq("id", previous.id);
      }

      const path = `${user.id}/${Date.now()}-${safeFileName(file.name)}`;
      const { error: uploadError } = await supabase.storage.from("resumes").upload(path, file);

      if (uploadError) {
        setError(uploadError.message);
        setLoading(false);
        return;
      }

      const { error: insertError } = await supabase.from("resumes").insert({
        user_id: user.id,
        storage_path: path,
        file_name: safeFileName(file.name),
        mime_type: file.type || "application/octet-stream",
        is_primary: true,
      });

      if (insertError) {
        setError(insertError.message);
        setLoading(false);
        return;
      }

      // Best-effort cleanup — an orphaned old file costs storage, not correctness or
      // security, so failure here should not block onboarding.
      if (previous?.storage_path) {
        await supabase.storage.from("resumes").remove([previous.storage_path]).catch(() => {});
      }
    }

    await supabase.from("profiles").update({ onboarding_step: 1 }).eq("id", user.id);
    router.push("/onboarding/work-history");
  }

  return (
    <OnboardingWizard currentStep={0}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="resume">Resume file (optional)</Label>
            <Input
              id="resume"
              type="file"
              accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
            <p className="text-xs text-muted-foreground">
              PDF, Word or text, up to 10 MB. Nothing reads it automatically yet — you&apos;ll enter
              your work history yourself on the next step, so this is optional and you can skip it.
            </p>
            {file && (
              <p className="text-xs text-muted-foreground">
                Selected: {file.name} ({Math.round(file.size / 1024)} KB)
              </p>
            )}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleContinue} disabled={loading}>
            {loading ? tc("loading") : file ? tc("continue") : "Skip for now"}
          </Button>
        </CardContent>
      </Card>
    </OnboardingWizard>
  );
}
