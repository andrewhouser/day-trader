import { expect, test } from "@playwright/test";

const mockAlerts = [
  {
    message: "SPY position exceeds 30% of portfolio",
    severity: "high",
    ticker: "SPY",
    type: "concentration",
  },
];

const mockStressTest = {
  current_portfolio_value: 100000,
  scenarios: [
    {
      description: "Equity markets drop 20%",
      forced_reduction_cost: null,
      name: "Bear Market",
      pct_change: -18.5,
      positions_oversized: [],
      positions_stopped_out: [],
      shocked_value: 81500,
      summary: "Portfolio would lose $18,500.",
    },
  ],
  timestamp: "2026-01-01T10:00:00Z",
};

test.describe("Risk page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/risk/alerts", (route) =>
      route.fulfill({
        body: JSON.stringify(mockAlerts),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.route("**/api/risk/stress-test", (route) =>
      route.fulfill({
        body: JSON.stringify(mockStressTest),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.goto("/risk");
  });

  test("renders risk alert message", async ({ page }) => {
    await expect(page.getByText(/SPY position exceeds/)).toBeVisible();
  });

  test("renders stress test scenario", async ({ page }) => {
    await expect(page.getByText("Bear Market")).toBeVisible();
  });

  test("renders scenario pct change", async ({ page }) => {
    await expect(page.getByText("-18.5%")).toBeVisible();
  });

  test("renders Re-run button for stress test", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Re-run" })).toBeVisible();
  });
});
