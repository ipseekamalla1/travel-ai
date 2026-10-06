"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";

import { TextField } from "@/components/forms/text-field";
import { Button } from "@/components/ui/button";
import { applyServerErrors, safeNextPath } from "@/lib/forms";

import { useRegister } from "../hooks";
import { PASSWORD_MIN_LENGTH, registerSchema, type RegisterValues } from "../schemas";
import { FormAlert } from "./form-alert";

export function RegisterForm() {
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next"));
  const registerUser = useRegister();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await registerUser.mutateAsync(values);
      router.replace(next);
    } catch (error) {
      applyServerErrors(error, setError, ["display_name", "email", "password"]);
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5">
      <FormAlert message={errors.root?.server?.message} />
      <TextField
        label="What should we call you?"
        autoComplete="given-name"
        error={errors.display_name?.message}
        {...register("display_name")}
      />
      <TextField
        label="Email"
        type="email"
        autoComplete="email"
        inputMode="email"
        error={errors.email?.message}
        {...register("email")}
      />
      <TextField
        label="Password"
        type="password"
        autoComplete="new-password"
        hint={`At least ${PASSWORD_MIN_LENGTH} characters. A short phrase works well.`}
        error={errors.password?.message}
        {...register("password")}
      />
      <Button
        type="submit"
        size="lg"
        className="h-11 rounded-full text-base"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Creating your account…" : "Create account"}
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-medium text-foreground underline-offset-4 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
