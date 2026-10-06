/** Central TanStack Query keys, so invalidation targets are consistent across features. */
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
} as const;
