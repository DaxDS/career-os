import createMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";
import { routing } from "@/i18n/routing";
import { updateSession } from "@/lib/supabase/middleware";

const intlMiddleware = createMiddleware(routing);

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/api") || pathname.startsWith("/auth")) {
    return updateSession(request);
  }

  const intlResponse = intlMiddleware(request);
  const sessionResponse = await updateSession(request);

  if (sessionResponse.status !== 200 || sessionResponse.headers.get("location")) {
    return sessionResponse;
  }

  intlResponse.cookies.getAll().forEach((cookie) => {
    sessionResponse.cookies.set(cookie.name, cookie.value);
  });

  return intlResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
