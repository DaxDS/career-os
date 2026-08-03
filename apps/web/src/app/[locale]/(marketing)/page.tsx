"use client";

import { useTranslations } from "next-intl";
import { PLANS } from "@careeros/shared";
import { MarketingFooter, MarketingHeader } from "@/components/marketing/marketing-chrome";
import { DrawBoard } from "@/components/marketing/draw-board";
import { LandingJobExample } from "@/components/marketing/landing-job-example";
import { LandingScoreDemo } from "@/components/marketing/landing-score-demo";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/routing";
import { cn } from "@/lib/utils";

const HOW_IT_WORKS_STEPS = ["discover", "score", "routes", "approve"] as const;
const DIFFERENTIATORS = ["reviewQueue", "pathwayScoring", "permitFilters"] as const;

export default function LandingPage() {
  const t = useTranslations("landing");
  const td = useTranslations("disclaimer");

  return (
    <div className="landing-gradient flex min-h-screen flex-col">
      <MarketingHeader />

      <main className="flex-1">
        <section className="mx-auto max-w-4xl px-4 pb-8 pt-16 text-center sm:pt-20 md:pt-24">
          <h1 className="font-display mx-auto mb-6 max-w-3xl text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl md:leading-tight">
            {t("hero.title")}
          </h1>
          <p className="mx-auto mb-6 max-w-2xl text-base text-muted-foreground sm:text-lg">
            {t("hero.subtitle")}
          </p>
          {/* One primary action. The secondary link is a preview, not a competing
              destination — a second "start" button splits intent and costs signups. */}
          <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/signup"
              className={cn(buttonVariants({ size: "lg" }), "w-full sm:w-auto")}
            >
              {t("hero.ctaPrimary")}
            </Link>
            <Link
              href="/login"
              className={cn(buttonVariants({ variant: "ghost", size: "lg" }), "w-full sm:w-auto")}
            >
              {t("hero.ctaDemo")}
            </Link>
          </div>
          <p className="mx-auto mt-6 max-w-xl text-sm text-muted-foreground">
            {t("hero.tagline")}
          </p>
        </section>

        <LandingScoreDemo />

        <DrawBoard />

        <section className="border-y border-border/60 bg-card/30 py-12 sm:py-16">
          <div className="mx-auto max-w-6xl px-4">
            <ul className="grid gap-6 md:grid-cols-3 md:gap-8">
              {DIFFERENTIATORS.map((key) => (
                <li key={key} className="rounded-xl border border-border bg-card p-5 sm:p-6">
                  <h2 className="font-semibold">{t(`differentiators.${key}.title`)}</h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t(`differentiators.${key}.body`)}
                  </p>
                </li>
              ))}
            </ul>
            <p className="mx-auto mt-8 max-w-3xl text-center text-xs text-muted-foreground sm:text-sm">
              {td("pathway")}
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
          <h2 className="mb-3 text-center text-2xl font-bold sm:text-3xl">{t("howItWorks.title")}</h2>
          <p className="mx-auto mb-10 max-w-2xl text-center text-sm text-muted-foreground sm:text-base">
            {t("howItWorks.subtitle")}
          </p>
          <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {HOW_IT_WORKS_STEPS.map((step, index) => (
              <li key={step} className="relative rounded-xl border border-border bg-card p-5">
                <span className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-sm font-bold text-primary">
                  {index + 1}
                </span>
                <h3 className="font-semibold">{t(`howItWorks.steps.${step}.title`)}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {t(`howItWorks.steps.${step}.body`)}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section className="border-y border-border/60 bg-card/20 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4">
            <h2 className="mb-3 text-center text-2xl font-bold sm:text-3xl">
              {t("jobExample.title")}
            </h2>
            <p className="mx-auto mb-8 max-w-2xl text-center text-sm text-muted-foreground sm:text-base">
              {t("jobExample.subtitle")}
            </p>
            <LandingJobExample />
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
          <h2 className="mb-3 text-center text-2xl font-bold sm:text-3xl">{t("pricing.title")}</h2>
          <p className="mx-auto mb-10 max-w-2xl text-center text-sm text-muted-foreground sm:text-base">
            {t("pricing.subtitle")}
          </p>
          <div className="mx-auto grid max-w-3xl gap-4 sm:grid-cols-2 sm:gap-6">
            <div className="rounded-xl border border-border bg-card p-5 sm:p-6">
              <h3 className="text-lg font-semibold">{PLANS.free.label}</h3>
              <p className="mt-1 text-2xl font-bold">
                {t("pricing.freePrice")}
                <span className="text-sm font-normal text-muted-foreground">
                  {" "}
                  {t("pricing.perMonth")}
                </span>
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>{t("pricing.freeSends")}</li>
                <li>{t("pricing.freeTailored")}</li>
                <li>{t("pricing.reviewQueue")}</li>
              </ul>
              <Link href="/signup" className={cn(buttonVariants(), "mt-6 w-full")}>
                {t("pricing.getStarted")}
              </Link>
            </div>
            <div className="rounded-xl border border-primary/40 bg-primary/5 p-5 sm:p-6">
              <h3 className="text-lg font-semibold">{PLANS.pro.label}</h3>
              <p className="mt-1 text-2xl font-bold">
                {t("pricing.proPrice", { price: PLANS.pro.priceMonthlyCad })}
                <span className="text-sm font-normal text-muted-foreground">
                  {" "}
                  {t("pricing.perMonth")}
                </span>
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>{t("pricing.proSends")}</li>
                <li>{t("pricing.proTailored")}</li>
                <li>{t("pricing.proPathway")}</li>
              </ul>
              <Link
                href="/pricing"
                className={cn(buttonVariants({ variant: "outline" }), "mt-6 w-full")}
              >
                {t("pricing.viewPricing")}
              </Link>
            </div>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
