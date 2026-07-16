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

export default function ResumeUploadStep() {
  const t = useTranslations("onboarding.resume");
  const tc = useTranslations("common");
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleContinue() {
    if (!file) {
      setError("Please upload a resume to continue.");
      return;
    }

    setLoading(true);
    setError(null);

    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      router.push("/login");
      return;
    }

    const path = `${user.id}/${Date.now()}-${file.name}`;
    const { error: uploadError } = await supabase.storage.from("resumes").upload(path, file);

    if (uploadError) {
      setError(uploadError.message);
      setLoading(false);
      return;
    }

    await supabase.from("resumes").insert({
      user_id: user.id,
      storage_path: path,
      file_name: file.name,
      mime_type: file.type,
      is_primary: true,
    });

    await supabase
      .from("profiles")
      .update({ onboarding_step: 1 })
      .eq("id", user.id);

    // Phase 2: agent resume_parser will populate work_history from this file
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
            <Label htmlFor="resume">Resume file</Label>
            <Input
              id="resume"
              type="file"
              accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <p className="text-xs text-muted-foreground">{t("uploadHint")}</p>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleContinue} disabled={loading}>
            {loading ? tc("loading") : tc("continue")}
          </Button>
        </CardContent>
      </Card>
    </OnboardingWizard>
  );
}
