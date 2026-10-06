export type LifecycleStage = { name: string; summary: string };

/** The product lifecycle (docs/PRODUCT.md §1). Shared by the landing and how-it-works pages. */
export const LIFECYCLE: readonly LifecycleStage[] = [
  { name: "Dream", summary: "Collect the places and destinations that pull at you." },
  { name: "Discover", summary: "Save what fits, reject what doesn't — both teach the system." },
  { name: "Plan", summary: "Describe the trip in your own words and get a real, editable plan." },
  { name: "Explore", summary: "A calm companion that knows where you are and what's next." },
  { name: "Remember", summary: "Your places, meals, notes and spending, kept together." },
  { name: "Learn", summary: "Every trip sharpens what the system knows about you." },
];
