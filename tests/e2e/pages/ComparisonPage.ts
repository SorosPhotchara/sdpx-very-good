import type { Locator, Page } from "@playwright/test";

export class ComparisonPage {
  readonly rosterInput: Locator;
  readonly importButton: Locator;
  readonly importSuccess: Locator;
  readonly importError: Locator;
  readonly publishButton: Locator;
  readonly publishResult: Locator;

  constructor(private readonly page: Page) {
    this.rosterInput = page.getByLabel("Roster CSV");
    this.importButton = page.getByTestId("import-roster");
    this.importSuccess = page.getByTestId("import-success");
    this.importError = page.getByTestId("import-error");
    this.publishButton = page.getByTestId("publish-roster");
    this.publishResult = page.getByTestId("publish-result");
  }

  async goto() {
    await this.page.goto("/");
  }

  async importRoster(csv: string) {
    await this.rosterInput.fill(csv);
    await this.importButton.click();
  }

  async publishPreview() {
    await this.publishButton.click();
  }
}