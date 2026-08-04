import type { Metadata } from "next";

import ForgotPasswordPage from "./forgot-password-page";

export const metadata: Metadata = {
  title: "Reset your password — CareerOS",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <ForgotPasswordPage />;
}
