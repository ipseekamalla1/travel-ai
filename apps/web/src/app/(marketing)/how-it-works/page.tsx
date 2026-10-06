import type { Metadata } from "next";

import { LIFECYCLE } from "@/features/marketing/lifecycle";

export const metadata: Metadata = { title: "How it works" };

const STEPS = [
  {
    title: "Tell us how you travel",
    body: "A two-minute profile: your pace, budget style, food and activity interests, how much you like to walk.",
  },
  {
    title: "Describe the trip",
    body: "“Seven relaxed days in Japan, amazing food, some shopping, not too much walking.” We turn it into clear requirements you can check and edit.",
  },
  {
    title: "Get a real plan",
    body: "Places come from live providers. Days are scheduled around opening hours, travel time and your pace — with a reason for every pick.",
  },
  {
    title: "Adjust it together",
    body: "Drag things around, or ask. When the assistant suggests a change, you see exactly what will move before you accept.",
  },
] as const;

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-16 sm:px-8 sm:py-24">
      <h1 className="text-4xl font-semibold sm:text-5xl">How it works</h1>
      <ol className="mt-12 space-y-10">
        {STEPS.map((step, index) => (
          <li key={step.title} className="grid grid-cols-[2.5rem_1fr] gap-4">
            <span aria-hidden="true" className="font-heading text-2xl text-primary tabular-nums">
              {index + 1}
            </span>
            <div>
              <h2 className="text-2xl font-semibold">{step.title}</h2>
              <p className="mt-2 text-muted-foreground">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>

      <h2 className="mt-20 text-3xl font-semibold">Before, during and after</h2>
      <dl className="mt-8 grid gap-6 sm:grid-cols-2">
        {LIFECYCLE.map((stage) => (
          <div key={stage.name}>
            <dt className="font-semibold">{stage.name}</dt>
            <dd className="mt-1 text-muted-foreground">{stage.summary}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
