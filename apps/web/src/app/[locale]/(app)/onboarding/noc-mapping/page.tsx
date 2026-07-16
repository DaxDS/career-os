"use client";

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { createClient } from "@/lib/supabase/client";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface WorkRole {
  id: string;
  title: string;
  employer: string | null;
  duties_text: string | null;
  mapped_noc_code: string | null;
  mapped_teer: number | null;
  noc_confirmed: boolean;
}

export default function NocMappingStep() {
  const t = useTranslations("onboarding.nocMapping");
  const tc = useTranslations("common");
  const router = useRouter();
  const [roles, setRoles] = useState<WorkRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      const { data } = await supabase
        .from("work_history")
        .select("id, title, employer, duties_text, mapped_noc_code, mapped_teer, noc_confirmed")
        .eq("user_id", user.id)
        .order("sort_order");

      setRoles(data ?? []);
      setLoading(false);
    }
    load();
  }, []);

  function updateRole(id: string, field: keyof WorkRole, value: string | number | boolean) {
    setRoles((prev) =>
      prev.map((role) => (role.id === id ? { ...role, [field]: value } : role))
    );
  }

  async function handleContinue() {
    setSaving(true);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return;

    for (const role of roles) {
      await supabase
        .from("work_history")
        .update({
          mapped_noc_code: role.mapped_noc_code,
          mapped_teer: role.mapped_teer,
          noc_confirmed: Boolean(role.mapped_noc_code && role.mapped_teer !== null),
        })
        .eq("id", role.id);
    }

    await supabase.from("profiles").update({ onboarding_step: 3 }).eq("id", user.id);
    router.push("/onboarding/permit-status");
  }

  if (loading) return <p>{tc("loading")}</p>;

  return (
    <OnboardingWizard currentStep={2}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {roles.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No work history found. Go back and add at least one role.
            </p>
          )}
          {roles.map((role) => (
            <div key={role.id} className="space-y-3 rounded-lg border p-4">
              <div>
                <p className="font-medium">{role.title}</p>
                {role.employer && (
                  <p className="text-sm text-muted-foreground">{role.employer}</p>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>NOC 2021 unit group code</Label>
                  <Input
                    placeholder="e.g. 21231"
                    value={role.mapped_noc_code ?? ""}
                    onChange={(e) => updateRole(role.id, "mapped_noc_code", e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Phase 2: agent will suggest codes from noc_2021.json
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>TEER level (0–5)</Label>
                  <Input
                    type="number"
                    min={0}
                    max={5}
                    value={role.mapped_teer ?? ""}
                    onChange={(e) =>
                      updateRole(role.id, "mapped_teer", parseInt(e.target.value, 10))
                    }
                  />
                </div>
              </div>
            </div>
          ))}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/onboarding/work-history")}>
              {tc("back")}
            </Button>
            <Button onClick={handleContinue} disabled={saving}>
              {saving ? tc("loading") : tc("continue")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </OnboardingWizard>
  );
}
