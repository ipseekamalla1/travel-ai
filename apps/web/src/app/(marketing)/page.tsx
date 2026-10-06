import Link from "next/link";

import { Button } from "@/components/ui/button";
import { LIFECYCLE } from "@/features/marketing/lifecycle";

const PRINCIPLES = [
  {
    title: "Real places, real hours",
    body: "Opening times, distances and weather come from live data providers — never invented.",
  },
  {
    title: "You stay in control",
    body: "Suggested changes arrive as proposals you accept or dismiss. Nothing moves silently.",
  },
  {
    title: "It learns how you travel",
    body: "What you save, skip and edit shapes the next recommendation — not a vanity score.",
  },
] as const;

export default function LandingPage() {
  return (
    <>
      <section className="mx-auto flex max-w-6xl flex-col gap-8 px-5 pt-16 pb-20 sm:px-8 sm:pt-28">
        <p className="text-sm font-medium tracking-widest text-primary uppercase">
          Your personal travel universe
        </p>
        <h1 className="max-w-3xl text-5xl leading-[1.05] font-semibold sm:text-7xl">
          Travel with an AI that understands how you travel.
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          Describe the trip you want in your own words. Get a plan built from real places, shaped
          around your pace, your budget and what you love — then let it adapt as you go.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg" className="h-11 rounded-full px-6 text-base">
            <Link href="/register">Start your universe</Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="h-11 rounded-full px-6 text-base">
            <Link href="/how-it-works">See how it works</Link>
          </Button>
        </div>
      </section>

      <section aria-labelledby="lifecycle-heading" className="border-y bg-card">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
          <h2 id="lifecycle-heading" className="text-3xl font-semibold">
            One trip feeds the next
          </h2>
          <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {LIFECYCLE.map((stage, index) => (
              <li key={stage.name} className="flex gap-4">
                <span
                  aria-hidden="true"
                  className="font-heading text-2xl text-primary/60 tabular-nums"
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3 className="text-xl font-semibold">{stage.name}</h3>
                  <p className="mt-1 text-muted-foreground">{stage.summary}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section
        aria-labelledby="principles-heading"
        className="mx-auto max-w-6xl px-5 py-20 sm:px-8"
      >
        <h2 id="principles-heading" className="sr-only">
          Principles
        </h2>
        <ul className="grid gap-10 md:grid-cols-3">
          {PRINCIPLES.map((principle) => (
            <li key={principle.title}>
              <h3 className="text-2xl font-semibold">{principle.title}</h3>
              <p className="mt-3 text-muted-foreground">{principle.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
