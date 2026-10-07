"use client";

import { LogOutIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/features/auth/hooks";

const APP_LINKS = [
  { href: "/universe", label: "Universe" },
  { href: "/profile", label: "Profile" },
] as const;

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  const signOut = () => {
    // Navigate whatever happens: the cookie is cleared server-side when reachable, and the
    // proxy/RequireAuth gate handles anything left over.
    logout.mutate(undefined, { onSettled: () => router.replace("/") });
  };

  return (
    <header className="mx-auto flex w-full max-w-6xl items-center gap-2 px-5 py-4 sm:gap-6 sm:px-8">
      <Link
        href="/universe"
        className="hidden rounded-md font-heading text-lg font-semibold tracking-tight focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none sm:inline"
      >
        AI Travel Universe
      </Link>
      <nav aria-label="App" className="mr-auto">
        <ul className="flex items-center gap-1 text-sm">
          {APP_LINKS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className="rounded-full px-3 py-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none aria-[current=page]:bg-muted aria-[current=page]:text-foreground"
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
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
