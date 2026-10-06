import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthFormSkeleton } from "@/features/auth/components/form-skeleton";
import { RegisterForm } from "@/features/auth/components/register-form";

export const metadata: Metadata = { title: "Create your account" };

export default function RegisterPage() {
  return (
    <>
      <h1 className="text-3xl font-semibold">Start your travel universe</h1>
      <p className="mt-2 mb-8 text-muted-foreground">
        One account for every trip — before, during and after.
      </p>
      <Suspense fallback={<AuthFormSkeleton fields={3} />}>
        <RegisterForm />
      </Suspense>
    </>
  );
}
