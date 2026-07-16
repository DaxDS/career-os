"use client";

import { useRouter } from "@/i18n/routing";
import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function PrepareApplicationButton({ matchId, status }: { matchId: string; status: string }) {
  const router = useRouter();
  const t = useTranslations("billing");
  const tj = useTranslations("jobs");
  const tc = useTranslations("common");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPlanLimit, setIsPlanLimit] = useState(false);

  if (status === "queued" || status === "approved") {
    return (
      <Button variant="outline" size="sm" asChild>
        <Link href="/queue">{tj("viewInQueue")}</Link>
      </Button>
    );
  }

  async function handlePrepare() {
    setLoading(true);
    setError(null);
    setIsPlanLimit(false);
    try {
      const res = await fetch("/api/tailoring/prepare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ match_id: matchId }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 402) {
          setIsPlanLimit(true);
          setError(`${data.error} ${t("upgradeCta")}`);
          return;
        }
        throw new Error(data.error || "Failed");
      }
      router.push("/queue");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-1">
      <Button variant="default" size="sm" onClick={handlePrepare} disabled={loading}>
        {loading ? tc("loading") : tj("prepareApplication")}
      </Button>
      {error && (
        <p className="text-xs text-destructive">
          {error}{" "}
          {isPlanLimit && (
            <Link href="/settings" className="underline">
              {t("upgradeAtSettings")}
            </Link>
          )}
        </p>
      )}
    </div>
  );
}
