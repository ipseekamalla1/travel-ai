"use client";

import { LogOutIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/features/auth/hooks";

export function AppHeader() {
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  const signOut = () => {
    // Navigate whatever happens: the cookie is cleared server-side when reachable, and the
    // proxy/RequireAuth gate handles anything left over.
    logout.mutate(undefined, { onSettled: () => router.replace("/") });
  };

  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
      <Link
        href="/universe"
        className="rounded-md font-heading text-lg font-semibold tracking-tight focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        AI Travel Universe
      </Link>
      <div className="flex items-center gap-2">
        {user ? (
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {user.display_name}
          </span>
        ) : null}
        <Button
          variant="ghost"
          size="lg"
          onClick={signOut}
          disabled={logout.isPending}
          className="h-10 rounded-full"
        >
          <LogOutIcon aria-hidden="true" />
          {logout.isPending ? "Signing out…" : "Sign out"}
        </Button>
      </div>
    </header>
  );
}
