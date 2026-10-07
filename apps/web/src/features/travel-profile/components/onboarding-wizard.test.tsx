import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, renderWithClient } from "@/test/render";

import { OnboardingWizard } from "./onboarding-wizard";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

const opt = (value: string, label = value) => ({ value, label, description: "" });
const OPTIONS = {
  travel_styles: [opt("food", "Food-first"), opt("nature", "Nature & scenery")],
  max_travel_styles: 5,
  paces: [opt("relaxed", "Relaxed"), opt("balanced", "Balanced"), opt("packed", "Packed")],
  budget_styles: [opt("moderate", "Moderate"), opt("comfortable", "Comfortable")],
  accommodation_styles: [opt("boutique", "Boutique hotels")],
  walking_tolerances: [opt("low", "Keep walking short"), opt("medium", "Some walking is fine")],
  dietary: [opt("vegetarian", "Vegetarian")],
  preference_groups: [
    {
      id: "food",
      label: "Food & drink",
      keys: [{ key: "food.cafes", label: "Cafés & coffee", description: "" }],
    },
    {
      id: "style",
      label: "How you explore",
      keys: [{ key: "style.crowds", label: "Busy places", description: "" }],
    },
  ],
  currencies: ["USD"],
};
const PROFILE = {
  travel_styles: [],
  pace: "balanced",
  budget_style: "moderate",
  accommodation_style: null,
  walking_tolerance: "medium",
  dietary: [],
  day_start: "09:00:00",
  day_end: "21:00:00",
  onboarding_completed: false,
  preferences: [],
};

type Call = { method: string; path: string; body: unknown };
let calls: Call[] = [];

beforeEach(() => {
  calls = [];
  document.cookie = "atu_csrf=test-token";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const path = url.replace("/api/v1", "");
      const body = init?.body ? JSON.parse(init.body as string) : undefined;
      calls.push({ method, path, body });
      if (path === "/meta/travel-profile-options") return jsonResponse(200, OPTIONS);
      if (path === "/me/travel-profile/complete-onboarding")
        return jsonResponse(200, { ...PROFILE, onboarding_completed: true });
      if (path === "/auth/me") return jsonResponse(200, {});
      return jsonResponse(200, PROFILE);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockReset();
});

const writes = () => calls.filter((c) => c.method !== "GET");

describe("OnboardingWizard", () => {
  it("walks through every step and saves the answers on finish", async () => {
    const user = userEvent.setup();
    renderWithClient(<OnboardingWizard />);

    await user.click(await screen.findByLabelText("Food-first"));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("What pace feels right?");
    await user.click(screen.getByLabelText(/Relaxed/));
    await user.click(screen.getByLabelText(/Keep walking short/));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByLabelText("Vegetarian"));
    await user.click(screen.getByRole("radio", { name: "Love" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("radio", { name: "Not for me" }));
    await user.click(screen.getByRole("button", { name: "Finish" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/universe"));
    expect(writes().map((c) => `${c.method} ${c.path}`)).toEqual([
      "PUT /me/travel-profile",
      "PATCH /me/travel-profile/preferences",
      "POST /me/travel-profile/complete-onboarding",
    ]);
    expect(writes()[0]!.body).toMatchObject({
      travel_styles: ["food"],
      pace: "relaxed",
      walking_tolerance: "low",
      dietary: ["vegetarian"],
    });
    expect(writes()[1]!.body).toEqual({
      upsert: [
        { key: "food.cafes", weight: 1 },
        { key: "style.crowds", weight: -1 },
      ],
      remove: [],
      source: "onboarding",
    });
  });

  it("'Finish later' saves progress without completing onboarding", async () => {
    const user = userEvent.setup();
    renderWithClient(<OnboardingWizard />);

    await user.click(await screen.findByLabelText("Nature & scenery"));
    await user.click(screen.getByRole("button", { name: "Finish later" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/universe"));
    expect(writes().map((c) => c.path)).toEqual(["/me/travel-profile"]);
  });

  it("keeps answers and shows an error when saving fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/meta/travel-profile-options")) return jsonResponse(200, OPTIONS);
        if ((init?.method ?? "GET") === "GET") return jsonResponse(200, PROFILE);
        return jsonResponse(503, {
          code: "INTERNAL_ERROR",
          detail: "Service unavailable.",
          errors: [],
        });
      }),
    );
    const user = userEvent.setup();
    renderWithClient(<OnboardingWizard />);

    await user.click(await screen.findByLabelText("Food-first"));
    await user.click(screen.getByRole("button", { name: "Finish later" }));

    expect(await screen.findByText(/Your answers are still here/)).toBeInTheDocument();
    expect(screen.getByLabelText("Food-first")).toBeChecked();
    expect(replace).not.toHaveBeenCalled();
  });
});
