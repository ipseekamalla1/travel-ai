"use client";

import { useId } from "react";

import { cn } from "@/lib/utils";

import type { TravelProfileOptions } from "../api";
import { nearestLevel, RATING_LEVELS, type PreferenceWeights } from "../preferences";

type Group = TravelProfileOptions["preference_groups"][number];

/** One row per preference key: a 4-level radio group (Not for me / Neutral / Like / Love). */
export function PreferenceRatings({
  groups,
  weights,
  onChange,
}: {
  groups: readonly Group[];
  weights: PreferenceWeights;
  onChange: (key: string, weight: number) => void;
}) {
  return (
    <div className="grid gap-8">
      {groups.map((group) => (
        <section key={group.id} aria-labelledby={`pref-group-${group.id}`}>
          <h3 id={`pref-group-${group.id}`} className="mb-3 font-sans text-base font-semibold">
            {group.label}
          </h3>
          <ul className="grid gap-2">
            {group.keys.map((pref) => (
              <li key={pref.key}>
                <RatingRow
                  label={pref.label}
                  description={pref.description}
                  value={nearestLevel(weights[pref.key])}
                  onChange={(weight) => onChange(pref.key, weight)}
                />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function RatingRow({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  onChange: (weight: number) => void;
}) {
  const name = useId();
  return (
    <fieldset className="flex flex-col gap-2 rounded-xl border bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <legend className="sr-only">{label}</legend>
      <div aria-hidden="true">
        <p className="font-medium">{label}</p>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      <div className="flex gap-1">
        {RATING_LEVELS.map((level) => {
          const id = `${name}-${level.weight}`;
          return (
            <div key={level.weight}>
              <input
                id={id}
                type="radio"
                name={name}
                checked={value === level.weight}
                onChange={() => onChange(level.weight)}
                className="peer sr-only"
              />
              <label
                htmlFor={id}
                className={cn(
                  "block cursor-pointer rounded-full border px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors select-none",
                  "peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50 hover:border-primary/50",
                  level.weight < 0
                    ? "peer-checked:border-destructive/60 peer-checked:bg-destructive/10 peer-checked:text-destructive"
                    : "peer-checked:border-primary peer-checked:bg-accent peer-checked:text-accent-foreground",
                )}
              >
                {level.label}
              </label>
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
