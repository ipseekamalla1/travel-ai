"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChoiceGroup } from "@/components/forms/choice-group";
import { QueryErrorState } from "@/components/layout/query-error-state";
import { Button } from "@/components/ui/button";

import type { TravelProfile, TravelProfileOptions, TravelProfileUpdate } from "../api";
import { useSaveTravelProfile, useTravelProfile, useTravelProfileOptions } from "../hooks";
import { weightsFrom, type PreferenceWeights } from "../preferences";
import { toProfileUpdate } from "../profile";
import { PreferenceRatings } from "./preference-ratings";

const STEPS = [
  { id: "style", title: "How do you like to travel?" },
  { id: "pace", title: "What pace feels right?" },
  { id: "budget", title: "Budget and where you stay" },
  { id: "food", title: "Food & drink" },
  { id: "interests", title: "What do you enjoy?" },
] as const;

export function OnboardingWizard() {
  const options = useTravelProfileOptions();
  const profile = useTravelProfile();

  if (options.error || profile.error) {
    return (
      <QueryErrorState
        title="We couldn't load your profile."
        error={options.error ?? profile.error}
        onRetry={() => {
          void options.refetch();
          void profile.refetch();
        }}
      />
    );
  }
  if (!options.data || !profile.data) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label="Loading"
        className="h-96 animate-pulse rounded-3xl bg-muted"
      />
    );
  }
  return <Wizard options={options.data} profile={profile.data} />;
}

function Wizard({ options, profile }: { options: TravelProfileOptions; profile: TravelProfile }) {
  const router = useRouter();
  const save = useSaveTravelProfile();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<TravelProfileUpdate>(() => toProfileUpdate(profile));
  const [weights, setWeights] = useState<PreferenceWeights>(() => weightsFrom(profile.preferences));
  const headingRef = useRef<HTMLHeadingElement>(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    // Move focus to the new step's heading so screen-reader users hear where they are.
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  const update = (patch: Partial<TravelProfileUpdate>) => setDraft((d) => ({ ...d, ...patch }));
  const rate = (key: string, weight: number) => setWeights((w) => ({ ...w, [key]: weight }));
  const isLast = step === STEPS.length - 1;

  const finish = (complete: boolean) =>
    save.mutate(
      {
        profile: draft,
        weights,
        previous: profile,
        source: "onboarding",
        completeOnboarding: complete,
      },
      { onSuccess: () => router.replace("/universe") },
    );

  const foodGroups = options.preference_groups.filter((g) => g.id === "food");
  const otherGroups = options.preference_groups.filter((g) => g.id !== "food");

  return (
    <div className="grid gap-8">
      <div>
        <p className="text-sm font-medium text-muted-foreground">
          Step {step + 1} of {STEPS.length}
        </p>
        <div
          role="progressbar"
          aria-label="Onboarding progress"
          aria-valuemin={1}
          aria-valuemax={STEPS.length}
          aria-valuenow={step + 1}
          className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out-soft"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="mt-6 text-3xl font-semibold outline-none sm:text-4xl"
        >
          {STEPS[step]!.title}
        </h1>
      </div>

      {step === 0 && (
        <ChoiceGroup
          multiple
          legend="Pick what matters most"
          hint={`Choose up to ${options.max_travel_styles}.`}
          choices={options.travel_styles}
          value={draft.travel_styles}
          max={options.max_travel_styles}
          onChange={(travel_styles) => update({ travel_styles })}
        />
      )}

      {step === 1 && (
        <div className="grid gap-8">
          <ChoiceGroup
            legend="Daily pace"
            choices={options.paces}
            value={draft.pace}
            onChange={(pace) => update({ pace: pace as TravelProfileUpdate["pace"] })}
          />
          <ChoiceGroup
            legend="Walking"
            choices={options.walking_tolerances}
            value={draft.walking_tolerance}
            onChange={(walking_tolerance) =>
              update({
                walking_tolerance: walking_tolerance as TravelProfileUpdate["walking_tolerance"],
              })
            }
          />
        </div>
      )}

      {step === 2 && (
        <div className="grid gap-8">
          <ChoiceGroup
            legend="Budget style"
            choices={options.budget_styles}
            value={draft.budget_style}
            onChange={(budget_style) =>
              update({ budget_style: budget_style as TravelProfileUpdate["budget_style"] })
            }
          />
          <ChoiceGroup
            legend="Where you like to stay"
            layout="chips"
            choices={options.accommodation_styles}
            value={draft.accommodation_style ?? null}
            onChange={(accommodation_style) =>
              update({
                accommodation_style:
                  accommodation_style as TravelProfileUpdate["accommodation_style"],
              })
            }
          />
        </div>
      )}

      {step === 3 && (
        <div className="grid gap-8">
          <ChoiceGroup
            multiple
            layout="chips"
            legend="Dietary needs"
            hint="We'll only suggest places that work for you."
            choices={options.dietary}
            value={draft.dietary}
            onChange={(dietary) => update({ dietary })}
          />
          <PreferenceRatings groups={foodGroups} weights={weights} onChange={rate} />
        </div>
      )}

      {step === 4 && <PreferenceRatings groups={otherGroups} weights={weights} onChange={rate} />}

      {save.error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {save.error.message} Your answers are still here — try again.
        </p>
      ) : null}

      <div className="sticky bottom-0 -mx-5 flex flex-wrap items-center justify-between gap-3 border-t bg-background/95 px-5 py-4 backdrop-blur sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0">
        <Button
          variant="ghost"
          className="h-11 rounded-full px-4"
          onClick={() => finish(false)}
          disabled={save.isPending}
        >
          Finish later
        </Button>
        <div className="flex gap-2">
          {step > 0 ? (
            <Button
              variant="outline"
              className="h-11 rounded-full px-5"
              onClick={() => setStep((s) => s - 1)}
              disabled={save.isPending}
            >
              Back
            </Button>
          ) : null}
          {isLast ? (
            <Button
              className="h-11 rounded-full px-6"
              onClick={() => finish(true)}
              disabled={save.isPending}
            >
              {save.isPending ? "Saving…" : "Finish"}
            </Button>
          ) : (
            <Button className="h-11 rounded-full px-6" onClick={() => setStep((s) => s + 1)}>
              Continue
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
