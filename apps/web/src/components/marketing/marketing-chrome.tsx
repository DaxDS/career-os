"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/routing";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function MarketingHeader() {
  const t = useTranslations("marketing");

  return (
    <header className="border-b border-border/60 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:h-16">
        <Link href="/" className="shrink-0 text-lg font-bold text-primary sm:text-xl">
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="text-sm">
              ◆
            </span>
            Career OS
          </span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-4">
          <Link href="/pricing" className="hidden text-sm text-muted-foreground hover:text-foreground sm:inline">
            {t("nav.pricing")}
          </Link>
          <Link href="/login" className="hidden text-sm font-medium text-primary hover:underline sm:inline">
            {t("nav.demo")}
          </Link>
          <Link href="/privacy" className="text-sm text-muted-foreground hover:text-foreground">
            {t("nav.privacy")}
          </Link>
          <Link
            href="/login"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }), "hidden sm:inline-flex")}
          >
            {t("nav.login")}
          </Link>
          <Link href="/signup" className={cn(buttonVariants({ size: "sm" }))}>
            {t("nav.signup")}
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function MarketingFooter() {
  const t = useTranslations("marketing");
  const td = useTranslations("disclaimer");

  return (
    <footer className="border-t border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:py-12">
        <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-3">
          <div className="sm:col-span-2 md:col-span-1">
            <p className="font-bold text-primary">
              <span className="inline-flex items-center gap-2">
                <span aria-hidden>◆</span>
                Career OS
              </span>
            </p>
            <p className="mt-2 text-sm text-muted-foreground">{t("footer.tagline")}</p>
            <p className="mt-2 text-xs text-muted-foreground">{t("footer.hosting")}</p>
          </div>
          <div>
            <p className="text-sm font-medium">{t("footer.product")}</p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
              <li>
                <Link href="/pricing" className="hover:text-foreground">
                  {t("nav.pricing")}
                </Link>
              </li>
              <li>
                <Link href="/signup" className="hover:text-foreground">
                  {t("nav.signup")}
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-medium">{t("footer.legal")}</p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
              <li>
                <Link href="/privacy" className="hover:text-foreground">
                  {t("footer.privacy")}
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-foreground">
                  {t("footer.terms")}
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <p className="mt-8 text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} Career OS. {td("pathway")}
        </p>
      </div>
    </footer>
  );
}
