import type { Metadata } from "next";

import ResetPasswordPage from "./reset-password-page";

export const metadata: Metadata = {
  title: "Choose a new password — CareerOS",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <ResetPasswordPage />;
}
