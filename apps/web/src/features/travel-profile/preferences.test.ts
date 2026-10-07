import { describe, expect, it } from "vitest";

import { nearestLevel, preferencesPatch, weightsFrom } from "./preferences";

const stored = [
  { key: "food.cafes", weight: 1, source: "onboarding", updated_at: "2026-10-06T00:00:00Z" },
  { key: "style.crowds", weight: -1, source: "onboarding", updated_at: "2026-10-06T00:00:00Z" },
];

describe("preferencesPatch", () => {
  it("only sends what changed", () => {
    const next = { ...weightsFrom(stored), "food.wine": 0.5 };

    expect(preferencesPatch(stored, next, "explicit")).toEqual({
      upsert: [{ key: "food.wine", weight: 0.5 }],
      remove: [],
      source: "explicit",
    });
  });

  it("removes keys set back to neutral and upserts changed weights", () => {
    const next = { "food.cafes": 0.5, "style.crowds": 0 };

    expect(preferencesPatch(stored, next, "onboarding")).toEqual({
      upsert: [{ key: "food.cafes", weight: 0.5 }],
      remove: ["style.crowds"],
      source: "onboarding",
    });
  });

  it("never upserts a neutral weight for a key that was never stored", () => {
    expect(preferencesPatch([], { "food.bars": 0 }, "explicit").upsert).toEqual([]);
  });
});

describe("nearestLevel", () => {
  it.each([
    [undefined, 0],
    [1, 1],
    [0.4, 0.5],
    [0.8, 1],
    [-0.6, -1],
    [0.1, 0],
  ])("%s → %s", (weight, level) => {
    expect(nearestLevel(weight)).toBe(level);
  });
});
