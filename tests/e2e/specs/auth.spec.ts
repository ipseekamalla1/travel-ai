import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { PASSWORD, registerViaUi, uniqueEmail } from "../support/auth";

test.describe("authentication", () => {
  test("registration signs in and the session survives a reload", async ({ page }) => {
    await registerViaUi(page, "Maya", uniqueEmail("reg"));

    await expect(page.getByRole("heading", { level: 1 })).toContainText("Maya");
    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Maya");
  });

  test("protected pages redirect to login and come back after signing in", async ({ page }) => {
    const email = uniqueEmail("next");
    await registerViaUi(page, "Leo", email);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.goto("/universe");
    await expect(page).toHaveURL(/\/login\?next=%2Funiverse$/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/universe$/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Leo");
  });

  test("wrong password shows an error and stays on the login page", async ({ page }) => {
    const email = uniqueEmail("wrong");
    await registerViaUi(page, "Priya", email);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(
      page.getByRole("alert").filter({ hasText: "The email or password is incorrect." }),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("duplicate email is reported on the email field", async ({ page }) => {
    const email = uniqueEmail("dup");
    await registerViaUi(page, "First", email);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.goto("/register");
    await page.getByLabel("What should we call you?").fill("Second");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByText("This email is already registered.")).toBeVisible();
    await expect(page.getByLabel("Email")).toHaveAttribute("aria-invalid", "true");
  });

  test("signed-in users skip the auth pages", async ({ page }) => {
    await registerViaUi(page, "Ana", uniqueEmail("skip"));

    await page.goto("/login");

    await expect(page).toHaveURL(/\/universe$/);
  });

  test("a stale session cookie ends on the login page without looping", async ({
    page,
    context,
    baseURL,
  }) => {
    await context.addCookies([{ name: "atu_session", value: "revoked-or-garbage", url: baseURL! }]);

    await page.goto("/universe");

    await expect(page).toHaveURL(/\/login\?next=%2Funiverse$/);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });

  for (const path of ["/login", "/register"]) {
    test(`no detectable accessibility violations on ${path}`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByLabel("Email")).toBeVisible();

      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

      expect(results.violations).toEqual([]);
    });
  }

  test("no detectable accessibility violations on /universe", async ({ page }) => {
    await registerViaUi(page, "Axe", uniqueEmail("a11y"));
    await expect(page.locator("[aria-busy=true]")).toHaveCount(0);

    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

    expect(results.violations).toEqual([]);
  });
});
