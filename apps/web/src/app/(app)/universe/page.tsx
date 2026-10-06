import type { Metadata } from "next";

import { UniverseHome } from "@/features/universe/components/universe-home";

export const metadata: Metadata = { title: "Your universe" };

export default function UniversePage() {
  return <UniverseHome />;
}
