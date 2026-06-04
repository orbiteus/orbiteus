/** TanStack Query keys — stable for prefetch + invalidation. */

export const queryKeys = {
  shareView: (token: string) => ["portal", "share", token] as const,
};
