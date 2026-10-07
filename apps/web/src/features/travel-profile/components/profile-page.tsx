"use client";

import { QueryErrorState } from "@/components/layout/query-error-state";
import { AccountSettings } from "@/features/account/components/account-settings";
import { useCurrentUser } from "@/features/auth/hooks";

import { useTravelProfile, useTravelProfileOptions } from "../hooks";
import { ProfileEditor } from "./profile-editor";

export function ProfilePage() {
  const { data: user } = useCurrentUser();
  const options = useTravelProfileOptions();
  const profile = useTravelProfile();

  return (
    <div className="mx-auto grid max-w-3xl gap-14 px-5 pt-8 pb-16 sm:px-8 sm:pt-12">
      <h1 className="text-4xl font-semibold">Profile</h1>

      {options.error || profile.error ? (
        <QueryErrorState
          title="We couldn't load your profile."
          error={options.error ?? profile.error}
          onRetry={() => {
            void options.refetch();
            void profile.refetch();
          }}
        />
      ) : !user || !options.data || !profile.data ? (
        <div role="status" aria-busy="true" aria-label="Loading" className="grid gap-6">
          <div className="h-48 animate-pulse rounded-2xl bg-muted" />
          <div className="h-96 animate-pulse rounded-2xl bg-muted" />
        </div>
      ) : (
        <>
          <section aria-labelledby="account-heading" className="grid gap-6">
            <h2 id="account-heading" className="text-2xl font-semibold">
              Account
            </h2>
            <AccountSettings user={user} currencies={options.data.currencies} />
          </section>
          <section aria-labelledby="travel-heading" className="grid gap-6">
            <div>
              <h2 id="travel-heading" className="text-2xl font-semibold">
                How you travel
              </h2>
              <p className="mt-2 text-muted-foreground">
                This shapes every recommendation and plan we make for you.
              </p>
            </div>
            <ProfileEditor options={options.data} profile={profile.data} />
          </section>
        </>
      )}
    </div>
  );
}
