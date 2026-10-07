import type { Metadata } from "next";

import { OnboardingWizard } from "@/features/travel-profile/components/onboarding-wizard";

export const metadata: Metadata = { title: "Your travel style" };

export default function OnboardingPage() {
  return (
    <div className="mx-auto max-w-2xl px-5 pt-6 pb-16 sm:px-8 sm:pt-12">
      <OnboardingWizard />
    </div>
  );
}
