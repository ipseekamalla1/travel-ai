import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("foundation smoke", () => {
  test("landing page renders and navigates to how it works", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toContainText("understands how you travel");
    await page.getByRole("link", { name: "See how it works" }).click();

    await expect(page).toHaveURL(/\/how-it-works$/);
    await expect(page.getByRole("heading", { level: 1, name: "How it works" })).toBeVisible();
  });

  test("unknown routes show the not-found page", async ({ page }) => {
    const response = await page.goto("/definitely-not-a-page");

    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: /wandered off the map/ })).toBeVisible();
  });

  test("web proxies /api to the backend and it is ready", async ({ request }) => {
    const response = await request.get("/api/v1/health/ready");

    expect(response.status()).toBe(200);
    expect(response.headers()["x-request-id"]).toBeTruthy();
    expect(await response.json()).toEqual({
      status: "ok",
      components: { database: "ok", redis: "ok" },
    });
  });

  for (const path of ["/", "/how-it-works", "/about"]) {
    test(`no detectable accessibility violations on ${path}`, async ({ page }) => {
      await page.goto(path);

      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

      expect(results.violations).toEqual([]);
    });
  }
});
