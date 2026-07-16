import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import {
  resolveLocale,
  stripLocaleFromPathname,
  withLocalePrefix,
} from "@/lib/i18n-path";

export async function updateSession(request: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  const pathname = stripLocaleFromPathname(request.nextUrl.pathname);
  const locale = resolveLocale(request);

  const isAuthRoute =
    pathname.startsWith("/login") ||
    pathname.startsWith("/signup") ||
    pathname.startsWith("/auth");

  const isAppRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/onboarding") ||
    pathname.startsWith("/profile") ||
    pathname.startsWith("/jobs") ||
    pathname.startsWith("/pathways") ||
    pathname.startsWith("/queue") ||
    pathname.startsWith("/tracker") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/activity");

  if (!supabaseUrl || !supabaseAnonKey) {
    if (isAppRoute) {
      const url = request.nextUrl.clone();
      url.pathname = withLocalePrefix("/login", locale);
      url.searchParams.set("error", "supabase_not_configured");
      return NextResponse.redirect(url);
    }
    return NextResponse.next({ request });
  }

  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options?: Record<string, unknown> }[]) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options)
        );
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user && isAppRoute) {
    const url = request.nextUrl.clone();
    url.pathname = withLocalePrefix("/login", locale);
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  if (user && isAuthRoute && !pathname.startsWith("/auth/callback")) {
    const url = request.nextUrl.clone();
    url.pathname = withLocalePrefix("/dashboard", locale);
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
