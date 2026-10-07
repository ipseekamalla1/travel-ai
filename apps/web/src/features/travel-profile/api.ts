import type { ApiSchema } from "@atu/types";

import { apiFetch } from "@/lib/api/client";

export type TravelProfile = ApiSchema<"TravelProfileOut">;
export type TravelProfileUpdate = ApiSchema<"TravelProfileUpdate">;
export type TravelProfileOptions = ApiSchema<"TravelProfileOptions">;
export type PreferencesPatch = ApiSchema<"PreferencesPatch">;

export const travelProfileApi = {
  options: () => apiFetch<TravelProfileOptions>("/meta/travel-profile-options"),
  get: () => apiFetch<TravelProfile>("/me/travel-profile"),
  replace: (data: TravelProfileUpdate) =>
    apiFetch<TravelProfile>("/me/travel-profile", { method: "PUT", json: data }),
  patchPreferences: (patch: PreferencesPatch) =>
    apiFetch<TravelProfile>("/me/travel-profile/preferences", { method: "PATCH", json: patch }),
  completeOnboarding: () =>
    apiFetch<TravelProfile>("/me/travel-profile/complete-onboarding", { method: "POST" }),
};
