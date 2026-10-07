"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { TextField } from "@/components/forms/text-field";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { User } from "@/features/auth/api";
import { FormAlert } from "@/features/auth/components/form-alert";
import { queryKeys } from "@/lib/api/query-keys";
import { applyServerErrors } from "@/lib/forms";

import { accountApi } from "../api";

const schema = z.object({
  display_name: z.string().trim().min(1, "Tell us what to call you.").max(80),
  home_currency: z.string().length(3),
  units: z.enum(["metric", "imperial"]),
});
type Values = z.infer<typeof schema>;

export function AccountSettings({
  user,
  currencies,
}: {
  user: User;
  currencies: readonly string[];
}) {
  const queryClient = useQueryClient();
  const currencyId = useId();
  const update = useMutation({
    mutationFn: accountApi.update,
    onSuccess: (saved) => queryClient.setQueryData(queryKeys.auth.me, saved),
  });
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty, isSubmitSuccessful },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: user.display_name,
      home_currency: user.home_currency,
      units: user.units as Values["units"],
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      const saved = await update.mutateAsync(values);
      reset({
        display_name: saved.display_name,
        home_currency: saved.home_currency,
        units: saved.units as Values["units"],
      });
    } catch (error) {
      applyServerErrors(error, setError, ["display_name", "home_currency", "units"]);
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5">
      <FormAlert message={errors.root?.server?.message} />
      <TextField
        label="Name"
        autoComplete="given-name"
        error={errors.display_name?.message}
        {...register("display_name")}
      />
      <div className="grid gap-1.5">
        <Label htmlFor={currencyId}>Home currency</Label>
        <select
          id={currencyId}
          className="h-11 rounded-lg border border-input bg-transparent px-3 text-base focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          {...register("home_currency")}
        >
          {currencies.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </div>
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-sm font-medium">Units</legend>
        <div className="flex gap-4">
          {(["metric", "imperial"] as const).map((unit) => (
            <label key={unit} className="flex items-center gap-2 text-sm capitalize">
              <input
                type="radio"
                value={unit}
                className="size-4 accent-primary"
                {...register("units")}
              />
              {unit === "metric" ? "Metric (km)" : "Imperial (miles)"}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="flex items-center gap-3">
        <Button
          type="submit"
          className="h-11 rounded-full px-6"
          disabled={isSubmitting || !isDirty}
        >
          {isSubmitting ? "Saving…" : "Save account"}
        </Button>
        {isSubmitSuccessful && !isDirty && !errors.root ? (
          <p role="status" className="text-sm text-muted-foreground">
            Saved.
          </p>
        ) : null}
      </div>
    </form>
  );
}
