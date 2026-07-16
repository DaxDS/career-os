"use client";

import { useTranslations } from "next-intl";

/** Hero score card — matches career-os-daxds visual mockup. */
export function LandingScoreDemo() {
  const t = useTranslations("landing.scoreDemo");

  return (
    <div className="mx-auto w-full max-w-lg px-4 pb-4 pt-2">
      <div className="rounded-xl border border-border bg-card p-5 shadow-[0_8px_30px_rgba(0,0,0,0.35)]">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-base font-semibold">{t("title")}</p>
            <p className="text-sm text-muted-foreground">{t("meta")}</p>
          </div>
          <span className="inline-flex shrink-0 items-center rounded-full border border-primary/40 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            {t("prBadge")}
          </span>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-background px-3 py-2.5">
            <strong className="text-base">{t("overallScore")}</strong>
            <span className="text-xs text-muted-foreground">{t("overallLabel")}</span>
          </div>
          <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-background px-3 py-2.5">
            <strong className="text-base">{t("atsScore")}</strong>
            <span className="text-xs text-muted-foreground">{t("atsLabel")}</span>
          </div>
          <div className="flex flex-col gap-0.5 rounded-lg border border-primary/40 bg-background px-3 py-2.5">
            <strong className="text-base text-primary">{t("nocCode")}</strong>
            <span className="text-xs text-muted-foreground">{t("nocLabel")}</span>
          </div>
        </div>

        <p className="text-sm leading-relaxed text-muted-foreground">{t("caption")}</p>
      </div>
    </div>
  );
}
