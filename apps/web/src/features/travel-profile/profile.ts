import type { TravelProfile, TravelProfileUpdate } from "./api";

/** The editable (PUT) subset of a stored profile. */
export function toProfileUpdate(profile: TravelProfile): TravelProfileUpdate {
  const { travel_styles, pace, budget_style, accommodation_style, walking_tolerance } = profile;
  const { dietary, day_start, day_end } = profile;
  return {
    travel_styles,
    pace,
    budget_style,
    accommodation_style: accommodation_style ?? null,
    walking_tolerance,
    dietary,
    day_start,
    day_end,
  };
}
