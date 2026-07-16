"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useRouter } from "@/i18n/routing";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AuthConfirmPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Confirming your email…");

  useEffect(() => {
    const tokenHash = searchParams.get("token_hash");
    const type = searchParams.get("type") || "signup";

    if (!tokenHash) {
      setStatus("error");
      setMessage("Missing confirmation token. Use the link from your email or sign up again.");
      return;
    }

    const supabase = createClient();
    supabase.auth
      .verifyOtp({
        token_hash: tokenHash,
        type: type as "signup" | "email" | "recovery" | "invite" | "magiclink",
      })
      .then(({ error }) => {
        if (error) {
          setStatus("error");
          setMessage(error.message);
          return;
        }
        setStatus("success");
        setMessage("Email confirmed. Redirecting to onboarding…");
        router.replace("/onboarding");
        router.refresh();
      });
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Email confirmation</CardTitle>
          <CardDescription>CareerOS account verification</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className={status === "error" ? "text-destructive" : "text-muted-foreground"}>
            {message}
          </p>
          {status === "error" && (
            <Button className="w-full" onClick={() => router.push("/login")}>
              Back to login
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
