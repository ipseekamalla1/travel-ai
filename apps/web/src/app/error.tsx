"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function RouteError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main
      id="main"
      role="alert"
      className="mx-auto flex max-w-xl flex-1 flex-col items-start justify-center gap-5 px-5 py-24"
    >
      <h1 className="text-3xl font-semibold">Something went wrong.</h1>
      <p className="text-muted-foreground">
        This part of the page couldn&apos;t load. Your data is safe — try again.
      </p>
      {error.digest ? (
        <p className="font-mono text-xs text-muted-foreground">Reference: {error.digest}</p>
      ) : null}
      <Button onClick={() => retry()} className="rounded-full px-5">
        Try again
      </Button>
    </main>
  );
}
