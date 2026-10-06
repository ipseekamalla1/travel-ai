import { AppHeader } from "@/components/layout/app-header";
import { RequireAuth } from "@/features/auth/components/require-auth";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <RequireAuth>
      <AppHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
    </RequireAuth>
  );
}
