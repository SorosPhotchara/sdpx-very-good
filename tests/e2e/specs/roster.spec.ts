import { test, expect } from "../fixtures";
import { ComparisonPage } from "../pages/ComparisonPage";

test.describe("roster comparison workflow", () => {
  test("imports a valid roster and publishes its comparison preview", async ({ page }) => {
    const comparisonPage = new ComparisonPage(page);

    await comparisonPage.goto();
    await comparisonPage.importRoster(
      "email,group_name\na@uni.ac.th,Aurora\nb@uni.ac.th,Nova\nc@uni.ac.th,Orion",
    );
    await expect(comparisonPage.importSuccess).toContainText("3 students ready");

    await comparisonPage.publishPreview();
    await expect(comparisonPage.publishResult).toHaveText("Published 3 comparisons.");
  });

  test("rejects an invalid roster without showing a success state", async ({ page }) => {
    const comparisonPage = new ComparisonPage(page);

    await comparisonPage.goto();
    await comparisonPage.importRoster(
      "email,group_name\nnot-an-email,Aurora",
    );

    await expect(comparisonPage.importError).toContainText("invalid email");
    await expect(comparisonPage.importSuccess).toBeHidden();
  });
});