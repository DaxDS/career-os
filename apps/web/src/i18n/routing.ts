import { defineRouting } from "next-intl/routing";
import { createSharedPathnamesNavigation } from "next-intl/navigation";

export const routing = defineRouting({
  locales: ["en", "fr"],
  defaultLocale: "en",
  localePrefix: "as-needed",
});

export const { Link, redirect: intlRedirect, usePathname, useRouter } =
  createSharedPathnamesNavigation(routing);

export function redirect(...args: Parameters<typeof intlRedirect>): never {
  return intlRedirect(...args) as never;
}
