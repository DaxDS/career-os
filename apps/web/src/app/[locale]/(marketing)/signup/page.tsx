import { Suspense } from "react";
import SignupPage from "./signup-page";

export default function SignupRoute() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading…</div>}>
      <SignupPage />
    </Suspense>
  );
}
