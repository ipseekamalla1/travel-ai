"use client";

import { useId, useState } from "react";

import { ChoiceGroup } from "@/components/forms/choice-group";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import type { TravelProfile, TravelProfileOptions, TravelProfileUpdate } from "../api";
import { useSaveTravelProfile } from "../hooks";
import { weightsFrom, type PreferenceWeights } from "../preferences";
import { toProfileUpdate } from "../profile";
import { PreferenceRatings } from "./preference-ratings";

const toInputTime = (value: string) => value.slice(0, 5); // "09:00:00" → "09:00"

export function ProfileEditor({
  options,
  profile,
}: {
  options: TravelProfileOptions;
  profile: TravelProfile;
}) {
  const save = useSaveTravelProfile();
  const [draft, setDraft] = useState<TravelProfileUpdate>(() => toProfileUpdate(profile));
  const [weights, setWeights] = useState<PreferenceWeights>(() => weightsFrom(profile.preferences));
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const startId = useId();
  const endId = useId();

  const update = (patch: Partial<TravelProfileUpdate>) => {
    setDraft((d) => ({ ...d, ...patch }));
    setSavedAt(null);
  };
  const rate = (key: string, weight: number) => {
    setWeights((w) => ({ ...w, [key]: weight }));
    setSavedAt(null);
  };
  const dayWindowInvalid = toInputTime(draft.day_end) <= toInputTime(draft.day_start);

  const onSave = () =>
    save.mutate(
      { profile: draft, weights, previous: profile, source: "explicit" },
      { onSuccess: () => setSavedAt(Date.now()) },
    );

  return (
    <div className="grid gap-10">
      <ChoiceGroup
        multiple
        legend="Travel style"
        hint={`Up to ${options.max_travel_styles}.`}
        choices={options.travel_styles}
        value={draft.travel_styles}
        max={options.max_travel_styles}
        onChange={(travel_styles) => update({ travel_styles })}
      />
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
        onChange={(v) =>
          update({ walking_tolerance: v as TravelProfileUpdate["walking_tolerance"] })
        }
      />
      <ChoiceGroup
        legend="Budget style"
        choices={options.budget_styles}
        value={draft.budget_style}
        onChange={(v) => update({ budget_style: v as TravelProfileUpdate["budget_style"] })}
      />
      <ChoiceGroup
        legend="Where you like to stay"
        layout="chips"
        choices={options.accommodation_styles}
        value={draft.accommodation_style ?? null}
        onChange={(v) =>
          update({ accommodation_style: v as TravelProfileUpdate["accommodation_style"] })
        }
      />
      <ChoiceGroup
        multiple
        layout="chips"
        legend="Dietary needs"
        choices={options.dietary}
        value={draft.dietary}
        onChange={(dietary) => update({ dietary })}
      />

      <fieldset className="grid gap-3">
        <legend className="mb-1 text-lg font-semibold">Your day</legend>
        <p className="-mt-2 text-sm text-muted-foreground">
          When plans should usually start and end.
        </p>
        <div className="flex flex-wrap gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor={startId}>Start</Label>
            <Input
              id={startId}
              type="time"
              className="h-11 w-36 px-3 text-base"
              value={toInputTime(draft.day_start)}
              onChange={(e) => update({ day_start: `${e.target.value}:00` })}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor={endId}>End</Label>
            <Input
              id={endId}
              type="time"
              className="h-11 w-36 px-3 text-base"
              aria-invalid={dayWindowInvalid || undefined}
              aria-describedby={dayWindowInvalid ? `${endId}-error` : undefined}
              value={toInputTime(draft.day_end)}
              onChange={(e) => update({ day_end: `${e.target.value}:00` })}
            />
          </div>
        </div>
        {dayWindowInvalid ? (
          <p id={`${endId}-error`} className="text-sm text-destructive">
            Your day needs to end after it starts.
          </p>
        ) : null}
      </fieldset>

      <section aria-labelledby="interests-heading" className="grid gap-4">
        <h2 id="interests-heading" className="text-2xl font-semibold">
          Interests
        </h2>
        <PreferenceRatings groups={options.preference_groups} weights={weights} onChange={rate} />
      </section>

      {save.error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {save.error.message}
        </p>
      ) : null}

      <div className="sticky bottom-0 -mx-5 flex items-center gap-3 border-t bg-background/95 px-5 py-4 backdrop-blur sm:mx-0 sm:px-0">
        <Button
          className="h-11 rounded-full px-6"
          onClick={onSave}
          disabled={save.isPending || dayWindowInvalid}
        >
          {save.isPending ? "Saving…" : "Save travel profile"}
        </Button>
        {savedAt ? (
          <p role="status" className="text-sm text-muted-foreground">
            Saved.
          </p>
        ) : null}
      </div>
    </div>
  );
}
