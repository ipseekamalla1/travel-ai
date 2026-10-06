import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, renderWithClient } from "@/test/render";

import { LoginForm } from "./login-form";
import { RegisterForm } from "./register-form";

const replace = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => searchParams,
}));

const fetchMock = vi.fn<typeof fetch>();
const USER = {
  id: "u1",
  email: "maya@example.com",
  display_name: "Maya",
  home_currency: "USD",
  locale: "en",
  units: "metric",
  created_at: "2026-10-06T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "atu_csrf=test-token";
  searchParams = new URLSearchParams();
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
  replace.mockReset();
});

describe("LoginForm", () => {
  it("validates on the client without calling the API", async () => {
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter your email.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the server's message for invalid credentials", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(401, {
        code: "INVALID_CREDENTIALS",
        title: "Invalid email or password",
        detail: "The email or password is incorrect.",
        errors: [],
      }),
    );
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The email or password is incorrect.",
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("signs in and goes to a safe `next` destination", async () => {
    searchParams = new URLSearchParams({ next: "/universe?tab=saved" });
    fetchMock.mockResolvedValue(jsonResponse(200, USER));
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery-7");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/universe?tab=saved"));
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/auth/login");
    expect(JSON.parse(init!.body as string)).toEqual({
      email: "maya@example.com",
      password: "correct-horse-battery-7",
    });
  });

  it("ignores off-site `next` values", async () => {
    searchParams = new URLSearchParams({ next: "//evil.example/phish" });
    fetchMock.mockResolvedValue(jsonResponse(200, USER));
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery-7");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/universe"));
  });
});

describe("RegisterForm", () => {
  it("puts server field errors on the matching field", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(409, {
        code: "EMAIL_TAKEN",
        title: "Conflict",
        detail: "An account with this email already exists.",
        errors: [
          { field: "email", code: "EMAIL_TAKEN", message: "This email is already registered." },
        ],
      }),
    );
    const user = userEvent.setup();
    renderWithClient(<RegisterForm />);

    await user.type(screen.getByLabelText("What should we call you?"), "Maya");
    await user.type(screen.getByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery-7");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("This email is already registered.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("enforces the minimum password length before submitting", async () => {
    const user = userEvent.setup();
    renderWithClient(<RegisterForm />);

    await user.type(screen.getByLabelText("What should we call you?"), "Maya");
    await user.type(screen.getByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Use at least 10 characters.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
