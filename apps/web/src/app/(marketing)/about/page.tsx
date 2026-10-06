import type { Metadata } from "next";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-2xl px-5 py-16 sm:px-8 sm:py-24">
      <h1 className="text-4xl font-semibold sm:text-5xl">About</h1>
      <div className="mt-8 space-y-5 text-lg text-muted-foreground">
        <p>
          Planning a trip today means juggling saved map lists, blogs, spreadsheets and chat
          assistants that sound confident but don&apos;t know whether the museum is open on Mondays.
        </p>
        <p>
          AI Travel Universe is built on a simple idea: an assistant is only as good as what it
          knows about you and about the real world. So it learns your travel style from what you
          actually do, and it grounds every recommendation in live data — real places, real opening
          hours, real travel times.
        </p>
        <p>
          The AI explains and suggests. You decide. Every meaningful change is shown to you before
          it happens.
        </p>
      </div>
    </article>
  );
}
