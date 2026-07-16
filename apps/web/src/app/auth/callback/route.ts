import { NextResponse } from "next/server";
import { getAppOrigin } from "@/lib/app-url";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const redirect = searchParams.get("redirect") ?? "/dashboard";
  const appOrigin = getAppOrigin();
  const safeRedirect = redirect.startsWith("/") ? redirect : "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${appOrigin}${safeRedirect}`);
    }
  }

  return NextResponse.redirect(`${appOrigin}/login?error=auth_callback_failed`);
}
