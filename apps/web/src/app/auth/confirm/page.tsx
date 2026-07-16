import { Suspense } from "react";
import AuthConfirmPage from "./confirm-page";

export default function AuthConfirmRoute() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading…</div>}>
      <AuthConfirmPage />
    </Suspense>
  );
}
