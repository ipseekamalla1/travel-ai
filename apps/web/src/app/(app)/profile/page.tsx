import type { Metadata } from "next";

import { ProfilePage } from "@/features/travel-profile/components/profile-page";

export const metadata: Metadata = { title: "Profile" };

export default function Page() {
  return <ProfilePage />;
}
