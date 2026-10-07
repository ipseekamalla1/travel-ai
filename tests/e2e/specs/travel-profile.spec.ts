import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { registerViaUi, uniqueEmail } from "../support/auth";

test.describe("travel profile", () => {
  test("new users complete onboarding and see their real travel style", async ({ page }) => {
    await registerViaUi(page, "Maya", uniqueEmail("onb"), { skipOnboarding: false });

    await expect(page.getByRole("heading", { level: 1 })).toHaveText("How do you like to travel?");
    await page.getByText("Food-first", { exact: true }).click();
    await page.getByText("Romantic", { exact: true }).click();
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByText("Relaxed", { exact: true }).click();
    await page.getByText("Keep walking short", { exact: true }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByText("Vegetarian", { exact: true }).click();
    await page.getByRole("group", { name: "Street food" }).getByText("Love").click();
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByRole("group", { name: "Lively, busy places" }).getByText("Not for me").click();
    await page.getByRole("button", { name: "Finish", exact: true }).click();

    await expect(page).toHaveURL(/\/universe$/);
    const card = page.getByRole("region", { name: /Food-first, Romantic/ });
    await expect(card).toContainText("relaxed pace");
    await expect(card).toContainText("Keep walking short");
    await expect(card.getByRole("list").first()).toContainText("Street food");
    await expect(card).toContainText("Lively, busy places");
  });

  test("skipping onboarding leaves a prompt on the universe", async ({ page }) => {
    await registerViaUi(page, "Leo", uniqueEmail("skip-onb"), { skipOnboarding: false });

    await page.getByRole("button", { name: "Finish later" }).click();

    await expect(page).toHaveURL(/\/universe$/);
    await expect(page.getByRole("link", { name: "Set your travel style" })).toBeVisible();
  });

  test("profile edits persist across reloads", async ({ page }) => {
    await registerViaUi(page, "Priya", uniqueEmail("profile"));
    await page.getByRole("link", { name: "Profile" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Profile" })).toBeVisible();

    await page.getByLabel("Home currency").selectOption("JPY");
    await page.getByRole("button", { name: "Save account" }).click();
    const account = page.getByRole("region", { name: "Account" });
    const travel = page.getByRole("region", { name: "How you travel" });
    await expect(account.getByRole("status")).toHaveText("Saved.");

    await page.getByText("Packed", { exact: true }).click();
    await page.getByRole("group", { name: "Museums" }).getByText("Like").click();
    await page.getByRole("button", { name: "Save travel profile" }).click();
    // Wait for *this* section's save to finish before reloading.
    await expect(travel.getByRole("status")).toHaveText("Saved.");

    await page.reload();
    await expect(page.getByLabel("Home currency")).toHaveValue("JPY");
    await expect(page.getByRole("radio", { name: /Packed/ })).toBeChecked();
    await expect(page.getByRole("group", { name: "Museums" }).getByRole("radio", { name: "Like" })).toBeChecked();
  });

  for (const path of ["/onboarding", "/profile"]) {
    test(`no detectable accessibility violations on ${path}`, async ({ page }) => {
      await registerViaUi(page, "Axe", uniqueEmail(`a11y${path.replace("/", "-")}`));
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.locator("[aria-busy=true]")).toHaveCount(0);

      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

      expect(results.violations).toEqual([]);
    });
  }
});
