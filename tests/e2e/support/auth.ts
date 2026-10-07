import { expect, type Page } from "@playwright/test";

// Test-only credential for accounts created by the E2E suite.
export const PASSWORD = "correct-horse-battery-7";

export function uniqueEmail(testId: string): string {
  return `e2e-${testId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** Registers through the UI. New accounts land on onboarding; by default we then skip to Universe. */
export async function registerViaUi(
  page: Page,
  name: string,
  email: string,
  { skipOnboarding = true }: { skipOnboarding?: boolean } = {},
) {
  await page.goto("/register");
  await page.getByLabel("What should we call you?").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  if (skipOnboarding) {
    await page.goto("/universe");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(name);
  }
}
