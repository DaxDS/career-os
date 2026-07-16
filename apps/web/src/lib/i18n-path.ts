import { routing } from "@/i18n/routing";
import type { NextRequest } from "next/server";

type Locale = (typeof routing.locales)[number];

export function resolveLocale(request: NextRequest): Locale {
  const pathname = request.nextUrl.pathname;

  for (const locale of routing.locales) {
    if (locale === routing.defaultLocale) continue;
    if (pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)) {
      return locale as Locale;
    }
  }

  const cookieLocale = request.cookies.get("NEXT_LOCALE")?.value;
  if (cookieLocale && routing.locales.includes(cookieLocale as Locale)) {
    return cookieLocale as Locale;
  }

  return routing.defaultLocale;
}

export function getLocaleFromPathname(pathname: string): Locale {
  for (const locale of routing.locales) {
    if (locale === routing.defaultLocale) continue;
    if (pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)) {
      return locale as Locale;
    }
  }

  return routing.defaultLocale;
}

export function stripLocaleFromPathname(pathname: string): string {
  for (const locale of routing.locales) {
    if (locale === routing.defaultLocale) continue;
    if (pathname === `/${locale}`) return "/";
    if (pathname.startsWith(`/${locale}/`)) {
      return pathname.slice(locale.length + 1);
    }
  }

  return pathname;
}

export function withLocalePrefix(pathname: string, locale: Locale): string {
  if (locale === routing.defaultLocale) {
    return pathname;
  }

  return pathname === "/" ? `/${locale}` : `/${locale}${pathname}`;
}
