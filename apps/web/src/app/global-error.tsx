"use client";

// Replaces the root layout when it fails, so it must render its own <html> and avoid app styles
// that may not have loaded.
export default function GlobalError({
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", padding: "4rem 1.5rem", maxWidth: 560 }}>
        <h1>Something went wrong.</h1>
        <p>The app couldn&apos;t load. Please try again.</p>
        <button type="button" onClick={() => retry()} style={{ padding: "0.5rem 1rem" }}>
          Try again
        </button>
      </body>
    </html>
  );
}
