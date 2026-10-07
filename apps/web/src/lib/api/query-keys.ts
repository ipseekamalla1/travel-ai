/** Central TanStack Query keys, so invalidation targets are consistent across features. */
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  travelProfile: {
    options: ["travel-profile", "options"] as const,
    mine: ["travel-profile", "mine"] as const,
  },
} as const;
