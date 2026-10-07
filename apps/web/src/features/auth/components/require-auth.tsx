"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

import { authApi } from "../api";
import { useCurrentUser } from "../hooks";

/**
 * Client-side session gate for the app area. `proxy.ts` already redirects when there is no
 * cookie; this handles cookies the API no longer accepts (expired/revoked). The server remains
 * the authority — this only decides what to render.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: user, error, isPending, refetch } = useCurrentUser();
  const signedOut = error instanceof ApiError && error.status === 401;

  useEffect(() => {
    if (!signedOut) return;
    // Clear the stale cookie first so /login doesn't bounce us straight back here.
    void authApi
      .logout()
      .catch(() => undefined)
      .finally(() => router.replace(`/login?next=${encodeURIComponent(pathname)}`));
  }, [signedOut, pathname, router]);

  if (user) return <>{children}</>;

  if (error && !signedOut) {
    return (
      <div role="alert" className="mx-auto grid max-w-md gap-4 px-5 py-24">
        <h1 className="text-2xl font-semibold">We couldn&apos;t load your account.</h1>
        <p className="text-muted-foreground">{error.message}</p>
        <div>
          <Button onClick={() => void refetch()} className="rounded-full px-5">
            Try again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-busy={isPending || signedOut}
      aria-label="Loading"
      className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8"
    >
      <div className="h-10 w-64 animate-pulse rounded-lg bg-muted" />
      <div className="mt-6 h-40 animate-pulse rounded-2xl bg-muted" />
    </div>
  );
}
