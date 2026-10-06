import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main
      id="main"
      className="mx-auto flex max-w-xl flex-1 flex-col items-start justify-center gap-5 px-5 py-24"
    >
      <p className="text-sm font-medium tracking-widest text-primary uppercase">404</p>
      <h1 className="text-4xl font-semibold">This page wandered off the map.</h1>
      <p className="text-muted-foreground">The link may be outdated, or the page has moved.</p>
      <Button asChild className="rounded-full px-5">
        <Link href="/">Back to start</Link>
      </Button>
    </main>
  );
}
