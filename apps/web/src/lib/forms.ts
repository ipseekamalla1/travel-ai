import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api/client";

const FALLBACK_MESSAGE = "Something went wrong. Please try again.";

/**
 * Maps an API error onto a React Hook Form: field errors go to their fields, anything else becomes
 * a form-level `root.server` error. Returns the form-level message (if any) for display.
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  knownFields: readonly Path<T>[],
): string | null {
  if (!(error instanceof ApiError)) {
    setError("root.server", { message: FALLBACK_MESSAGE });
    return FALLBACK_MESSAGE;
  }

  let unmatched = false;
  for (const fieldError of error.fieldErrors) {
    const field = fieldError.field as Path<T>;
    if (knownFields.includes(field)) {
      setError(field, { message: fieldError.message }, { shouldFocus: true });
    } else {
      unmatched = true;
    }
  }

  if (error.fieldErrors.length === 0 || unmatched) {
    const message = error.message || FALLBACK_MESSAGE;
    setError("root.server", { message });
    return message;
  }
  return null;
}

/** Only allow same-site relative paths as post-login destinations (prevents open redirects). */
export function safeNextPath(next: string | null | undefined, fallback = "/universe"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  return next;
}
