"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/api/query-keys";

import { travelProfileApi, type TravelProfile, type TravelProfileUpdate } from "./api";
import { preferencesPatch, type PreferenceWeights } from "./preferences";

export function useTravelProfileOptions() {
  return useQuery({
    queryKey: queryKeys.travelProfile.options,
    queryFn: travelProfileApi.options,
    staleTime: Infinity, // registry only changes on deploy
  });
}

export function useTravelProfile() {
  return useQuery({ queryKey: queryKeys.travelProfile.mine, queryFn: travelProfileApi.get });
}

export type SaveProfileInput = {
  profile: TravelProfileUpdate;
  weights: PreferenceWeights;
  previous: TravelProfile;
  source: "onboarding" | "explicit";
  completeOnboarding?: boolean;
};

/** Saves core fields and preference changes together; optionally completes onboarding. */
export function useSaveTravelProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      profile,
      weights,
      previous,
      source,
      completeOnboarding,
    }: SaveProfileInput) => {
      let saved = await travelProfileApi.replace(profile);
      const patch = preferencesPatch(previous.preferences, weights, source);
      if (patch.upsert.length || patch.remove.length) {
        saved = await travelProfileApi.patchPreferences(patch);
      }
      if (completeOnboarding && !saved.onboarding_completed) {
        saved = await travelProfileApi.completeOnboarding();
      }
      return saved;
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.travelProfile.mine, saved);
      void queryClient.invalidateQueries({ queryKey: queryKeys.auth.me });
    },
  });
}
