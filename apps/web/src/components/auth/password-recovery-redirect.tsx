"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

/**
 * Sends a password-recovery session to the reset form, wherever it lands.
 *
 * A Supabase recovery link only arrives at /reset-password when the redirect it was
 * issued with survives validation. If the redirect is missing, or is not on the
 * project's allowed-redirect list, Supabase falls back to the configured Site URL —
 * which is usually the home page. The token is still consumed and a real recovery
 * session is established, so the user ends up silently signed in on the marketing
 * page with no way to set a password and no indication anything happened. That is
 * exactly what a locked-out customer experiences at the worst possible moment.
 *
 * Supabase emits a distinct PASSWORD_RECOVERY event for this, so the fix does not
 * depend on parsing URL fragments or on the dashboard being configured correctly.
 * Mounted app-wide because the whole point is that the landing page is unpredictable.
 */
export function PasswordRecoveryRedirect() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Already where we want them — nothing to do, and redirecting would loop.
    if (pathname?.includes("/reset-password")) return;

    const supabase = createClient();

    // The event only fires if the session is established after this mounts. When the
    // client consumes the URL fragment before hydration — which is the common case on
    // a fast page — the event has already passed, so the fragment is checked directly
    // as well. Either path alone leaves a race.
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    if (hash.includes("type=recovery")) {
      router.replace("/reset-password");
      return;
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") {
        router.replace("/reset-password");
      }
    });

    return () => subscription.unsubscribe();
  }, [router, pathname]);

  return null;
}
