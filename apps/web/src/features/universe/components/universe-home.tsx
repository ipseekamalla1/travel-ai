"use client";

import { useCurrentUser } from "@/features/auth/hooks";

function greetingFor(hour: number): string {
  if (hour < 5) return "Still up";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function UniverseHome() {
  const { data: user } = useCurrentUser();
  if (!user) return null; // RequireAuth renders the loading state

  return (
    <div className="mx-auto max-w-6xl px-5 pt-10 pb-20 sm:px-8 sm:pt-16">
      <p className="text-sm font-medium tracking-widest text-primary uppercase">Your universe</p>
      <h1 className="mt-3 text-4xl font-semibold sm:text-6xl">
        {greetingFor(new Date().getHours())}, {user.display_name}.
      </h1>

      <section
        aria-labelledby="first-trip-heading"
        className="mt-12 rounded-3xl border bg-card p-8 sm:p-12"
      >
        <h2 id="first-trip-heading" className="text-2xl font-semibold sm:text-3xl">
          Your travel universe starts here.
        </h2>
        <p className="mt-3 max-w-xl text-muted-foreground">
          This is where your upcoming trips, saved places and travel style will live. Trip planning
          and your travel profile are being built next — your account is ready for them.
        </p>
      </section>
    </div>
  );
}
