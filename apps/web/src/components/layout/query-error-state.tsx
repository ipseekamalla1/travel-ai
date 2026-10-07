"use client";

import { Button } from "@/components/ui/button";

/** Recoverable error for a data-dependent region (docs/UX.md §5). */
export function QueryErrorState({
  title,
  error,
  onRetry,
}: {
  title: string;
  error: Error | null;
  onRetry: () => void;
}) {
  return (
    <div role="alert" className="grid gap-3 rounded-2xl border bg-card p-6">
      <p className="font-semibold">{title}</p>
      {error?.message ? <p className="text-sm text-muted-foreground">{error.message}</p> : null}
      <div>
        <Button variant="outline" onClick={onRetry} className="rounded-full px-5">
          Try again
        </Button>
      </div>
    </div>
  );
}
