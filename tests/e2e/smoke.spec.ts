import { test, expect } from "@playwright/test";

test("homepage loads correctly", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/Pairwise/);
  await expect(page.getByTestId("main-nav")).toBeVisible();
});

test("main CTA is visible", async ({ page }) => {
  await page.goto("/");

  const cta = page.getByTestId("cta-primary");
  await expect(cta).toBeVisible();
  await expect(cta).toHaveText("Start comparing");
});
