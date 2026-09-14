import { test as base, expect } from "@playwright/test";

type TestFixtures = {
  cleanWorkspace: void;
};

export const test = base.extend<TestFixtures>({
  cleanWorkspace: [async ({ page }, use) => {
    await page.goto("/");
    await use();
  }, { auto: true }],
});

export { expect };