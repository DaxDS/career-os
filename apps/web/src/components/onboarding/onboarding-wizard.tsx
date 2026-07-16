"use client";

import { useTranslations } from "next-intl";
import { Progress } from "@/components/ui/progress";
import { ONBOARDING_STEPS, type OnboardingStepId } from "@/lib/onboarding/constants";

interface OnboardingWizardProps {
  currentStep: OnboardingStepId;
  children: React.ReactNode;
}

export function OnboardingWizard({ currentStep, children }: OnboardingWizardProps) {
  const t = useTranslations("onboarding");
  const progress = ((currentStep + 1) / ONBOARDING_STEPS.length) * 100;

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {ONBOARDING_STEPS.map((step) => (
            <span
              key={step.id}
              className={step.id === currentStep ? "font-medium text-primary" : ""}
            >
              {t(`steps.${step.key}`)}
              {step.id < ONBOARDING_STEPS.length - 1 ? " →" : ""}
            </span>
          ))}
        </div>
        <Progress value={progress} className="h-2" />
      </div>
      {children}
    </div>
  );
}
