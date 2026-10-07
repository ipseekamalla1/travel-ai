"use client";

import Link from "next/link";

import { QueryErrorState } from "@/components/layout/query-error-state";
import { Button } from "@/components/ui/button";

import type { TravelProfile, TravelProfileOptions } from "../api";
import { useTravelProfile, useTravelProfileOptions } from "../hooks";

type Labelled = { value: string; label: string };

function labelOf(options: readonly Labelled[], value: string | null | undefined): string | null {
  return options.find((o) => o.value === value)?.label ?? null;
}

/** Plain-language summary built only from what the user actually told us (no invented scores). */
export function describeTravelStyle(profile: TravelProfile, options: TravelProfileOptions) {
  const styles = profile.travel_styles
    .map((v) => labelOf(options.travel_styles, v))
    .filter((l): l is string => l !== null);
  const pace = labelOf(options.paces, profile.pace);
  const walking = labelOf(options.walking_tolerances, profile.walking_tolerance);
  const budget = labelOf(options.budget_styles, profile.budget_style);

  const keyLabels = new Map(
    options.preference_groups.flatMap((g) => g.keys.map((k) => [k.key, k.label] as const)),
  );
  const byWeight = [...profile.preferences].sort((a, b) => b.weight - a.weight);
  const loves = byWeight.filter((p) => p.weight >= 0.5).map((p) => keyLabels.get(p.key) ?? p.key);
  const avoids = byWeight.filter((p) => p.weight < 0).map((p) => keyLabels.get(p.key) ?? p.key);

  const facts = [
    styles.length ? styles.join(", ") : null,
    pace ? `${pace.toLowerCase()} pace` : null,
    walking,
    budget ? `${budget.toLowerCase()} budget` : null,
  ].filter((f): f is string => f !== null);

  return { summary: facts.join(" · "), loves, avoids };
}

export function TravelStyleCard() {
  const options = useTravelProfileOptions();
  const profile = useTravelProfile();

  if (options.error || profile.error) {
    return (
      <QueryErrorState
        title="We couldn't load your travel style."
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
        className="h-44 animate-pulse rounded-3xl bg-muted"
      />
    );
  }

  if (!profile.data.onboarding_completed) {
    return (
      <section aria-labelledby="style-heading" className="rounded-3xl border bg-card p-8 sm:p-12">
        <h2 id="style-heading" className="text-2xl font-semibold sm:text-3xl">
          Tell us how you travel.
        </h2>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Two minutes on your pace, budget and what you love — every plan starts from here.
        </p>
        <Button asChild className="mt-6 h-11 rounded-full px-6">
          <Link href="/onboarding">Set your travel style</Link>
        </Button>
      </section>
    );
  }

  const { summary, loves, avoids } = describeTravelStyle(profile.data, options.data);
  return (
    <section aria-labelledby="style-heading" className="rounded-3xl border bg-card p-8 sm:p-12">
      <p className="text-sm font-medium tracking-widest text-primary uppercase">
        Your travel style
      </p>
      <h2 id="style-heading" className="mt-3 text-2xl font-semibold sm:text-3xl">
        {summary || "Still taking shape"}
      </h2>
      {loves.length ? (
        <div className="mt-6">
          <h3 className="font-sans text-sm font-medium text-muted-foreground">You love</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {loves.map((label) => (
              <li
                key={label}
                className="rounded-full bg-accent px-3 py-1 text-sm text-accent-foreground"
              >
                {label}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {avoids.length ? (
        <div className="mt-4">
          <h3 className="font-sans text-sm font-medium text-muted-foreground">Not for you</h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {avoids.map((label) => (
              <li
                key={label}
                className="rounded-full border px-3 py-1 text-sm text-muted-foreground"
              >
                {label}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <Button asChild variant="outline" className="mt-8 h-10 rounded-full px-5">
        <Link href="/profile">Refine</Link>
      </Button>
    </section>
  );
}
