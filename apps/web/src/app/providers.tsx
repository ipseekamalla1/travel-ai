"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { createQueryClient } from "@/lib/api/query-client";

export function Providers({ children }: { children: ReactNode }) {
  // One client per browser session; created lazily so it is never shared between server requests.
  const [queryClient] = useState(createQueryClient);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
