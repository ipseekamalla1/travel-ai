import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { applyServerErrors, safeNextPath } from "./forms";

describe("safeNextPath", () => {
  it.each([
    ["/trips/123", "/trips/123"],
    ["/universe?tab=saved", "/universe?tab=saved"],
    [null, "/universe"],
    ["", "/universe"],
    ["https://evil.example", "/universe"],
    ["//evil.example", "/universe"],
    ["/\\evil.example", "/universe"],
    ["javascript:alert(1)", "/universe"],
  ])("%s → %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });
});

describe("applyServerErrors", () => {
  it("maps known field errors and returns no form-level message", () => {
    const setError = vi.fn();
    const error = new ApiError({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Invalid",
      fieldErrors: [{ field: "email", code: "X", message: "Bad email." }],
    });

    const message = applyServerErrors<{ email: string }>(error, setError, ["email"]);

    expect(message).toBeNull();
    expect(setError).toHaveBeenCalledWith(
      "email",
      { message: "Bad email." },
      { shouldFocus: true },
    );
  });

  it("uses a form-level error when the error has no fields", () => {
    const setError = vi.fn();
    const error = new ApiError({ status: 429, code: "RATE_LIMITED", message: "Slow down." });

    expect(applyServerErrors<{ email: string }>(error, setError, ["email"])).toBe("Slow down.");
    expect(setError).toHaveBeenCalledWith("root.server", { message: "Slow down." });
  });

  it("falls back to a generic message for unexpected errors", () => {
    const setError = vi.fn();

    expect(applyServerErrors<{ email: string }>(new Error("boom"), setError, ["email"])).toMatch(
      /try again/,
    );
  });
});
