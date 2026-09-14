import { describe, expect, test } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";
import { App } from "./App";

const html = renderToStaticMarkup(<App />);

describe("landing page", () => {
  test("shows the service name", () => {
    expect(html).toContain("Pairwise");
  });

  test("renders the navigation bar with its test id", () => {
    expect(html).toContain('data-testid="main-nav"');
    expect(html).toContain("How it works");
  });

  test("renders the main CTA with its test id", () => {
    expect(html).toContain('data-testid="cta-primary"');
    expect(html).toContain("Start comparing");
  });

  test("renders a placeholder for the main feature", () => {
    expect(html).toContain("Comparison workspace");
  });
});
