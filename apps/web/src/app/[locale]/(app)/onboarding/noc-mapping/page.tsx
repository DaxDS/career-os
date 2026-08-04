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
import { NOC_SOURCE_URL, isValidNocCode, nocLabel, searchNoc, teerFromNocCode } from "@/lib/crs/noc";

interface WorkRole {
  id: string;
  title: string;
  employer: string | null;
  duties_text: string | null;
  mapped_noc_code: string | null;
  mapped_teer: number | null;
  noc_confirmed: boolean;
}

function RoleMapper({
  role,
  onPick,
}: {
  role: WorkRole;
  onPick: (code: string, teer: number | null) => void;
}) {
  const [query, setQuery] = useState("");
  const results = searchNoc(query);
  const code = role.mapped_noc_code ?? "";
  const known = code ? nocLabel(code) : null;
  const codeValid = code === "" || isValidNocCode(code);

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div>
        <p className="font-medium">{role.title}</p>
        {role.employer && <p className="text-sm text-muted-foreground">{role.employer}</p>}
      </div>

      <div className="space-y-2">
        <Label>Search by occupation</Label>
        <Input
          placeholder="e.g. software, nurse, cook"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {results.length > 0 && (
          <ul className="divide-y rounded-md border">
            {results.map((g) => (
              <li key={g.code}>
                <button
                  type="button"
                  className="flex w-full items-baseline justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-muted"
                  onClick={() => {
                    onPick(g.code, g.teer);
                    setQuery("");
                  }}
                >
                  <span>
                    <span className="font-medium">{g.title}</span>
                    {g.exampleTitles.length > 0 && (
                      <span className="block text-xs text-muted-foreground">
                        {g.exampleTitles.slice(0, 3).join(" · ")}
                      </span>
                    )}
                  </span>
                  <span className="whitespace-nowrap text-xs text-muted-foreground">
                    {g.code} · TEER {g.teer}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {query.trim().length >= 2 && results.length === 0 && (
          <p className="text-xs text-muted-foreground">
            No match in our list — it covers common occupations only. Look yours up on{" "}
            <a
              href={NOC_SOURCE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              the official NOC site
            </a>{" "}
            and paste the five-digit code below.
          </p>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>NOC 2021 code</Label>
          <Input
            placeholder="e.g. 21231"
            inputMode="numeric"
            value={code}
            onChange={(e) => {
              const next = e.target.value.replace(/\D/g, "").slice(0, 5);
              onPick(next, teerFromNocCode(next));
            }}
          />
          {known && <p className="text-xs text-muted-foreground">{known}</p>}
          {!codeValid && <p className="text-xs text-destructive">A NOC 2021 code is five digits.</p>}
        </div>
        <div className="space-y-2">
          <Label>TEER level</Label>
          <Input value={role.mapped_teer ?? ""} readOnly disabled />
          {/* TEER is the second digit of the NOC code, so it is derived rather than
              asked for — users should not be made to look up something implied by the
              value they just entered. */}
          <p className="text-xs text-muted-foreground">Filled in automatically from the code.</p>
        </div>
      </div>
    </div>
  );
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

  function pick(id: string, code: string, teer: number | null) {
    setRoles((prev) =>
      prev.map((role) =>
        role.id === id ? { ...role, mapped_noc_code: code || null, mapped_teer: teer } : role
      )
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

  const unmapped = roles.filter((r) => !r.mapped_noc_code).length;

  return (
    <OnboardingWizard currentStep={2}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            Your NOC code decides which category-based rounds you qualify for. Search by what you actually do
            — the code and TEER fill themselves in.
          </p>

          {roles.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No work history found. Go back and add at least one role.
            </p>
          )}

          {roles.map((role) => (
            <RoleMapper key={role.id} role={role} onPick={(code, teer) => pick(role.id, code, teer)} />
          ))}

          {roles.length > 0 && unmapped > 0 && (
            <p className="text-sm text-muted-foreground">
              {unmapped} role{unmapped === 1 ? "" : "s"} still unmapped. You can continue and add codes later,
              but unmapped roles do not count toward category eligibility.
            </p>
          )}

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
