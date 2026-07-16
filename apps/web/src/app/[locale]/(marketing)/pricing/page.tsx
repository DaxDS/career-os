import { Suspense } from "react";
import PricingContent from "./pricing-content";

export default function PricingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <PricingContent />
    </Suspense>
  );
}
