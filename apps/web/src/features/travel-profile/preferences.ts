import type { PreferencesPatch, TravelProfile } from "./api";

/** key → weight in [-1, 1]; a missing key means "no opinion". */
export type PreferenceWeights = Record<string, number>;

export const RATING_LEVELS = [
  { weight: -1, label: "Not for me" },
  { weight: 0, label: "Neutral" },
  { weight: 0.5, label: "Like" },
  { weight: 1, label: "Love" },
] as const;

export function weightsFrom(preferences: TravelProfile["preferences"]): PreferenceWeights {
  return Object.fromEntries(preferences.map((p) => [p.key, p.weight]));
}

/** Minimal patch turning `previous` into `next`: changed keys upserted, cleared keys removed. */
export function preferencesPatch(
  previous: TravelProfile["preferences"],
  next: PreferenceWeights,
  source: "onboarding" | "explicit",
): PreferencesPatch {
  const before = weightsFrom(previous);
  const upsert = Object.entries(next)
    .filter(([key, weight]) => weight !== 0 && before[key] !== weight)
    .map(([key, weight]) => ({ key, weight }));
  const remove = Object.keys(before).filter((key) => !next[key]);
  return { upsert, remove, source };
}

/** Snap stored weights (which may be inferred later, e.g. 0.37) to the nearest UI level. */
export function nearestLevel(weight: number | undefined): number {
  if (weight === undefined) return 0;
  return RATING_LEVELS.reduce((best, level) =>
    Math.abs(level.weight - weight) < Math.abs(best.weight - weight) ? level : best,
  ).weight;
}
