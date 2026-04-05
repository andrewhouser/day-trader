import { expect, test } from "@playwright/test";

const mockTechnicals = {
  SPY: {
    atr_14: "8.50",
    bb_lower: "490.00",
    bb_upper: "520.00",
    macd_histogram: -0.32,
    price: "500.00",
    roc_20: "-1.5",
    rsi_14: 72.1,
    sma_20: "498.00",
    sma_200: "470.00",
    sma_50: "495.00",
    volume_ratio: "0.9",
  },
};

const mockRegime = {
  parameters: { strategy_note: "Use momentum strategies" },
  regime: "UPTREND",
  signals: { golden_cross: true, roc_20: 2.3, rsi: 55, vix: 18.5 },
  timestamp: "2026-01-01T10:00:00Z",
};

test.describe("Technicals", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/technicals", (route) =>
      route.fulfill({
        body: JSON.stringify(mockTechnicals),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.route("**/api/regime", (route) =>
      route.fulfill({
        body: JSON.stringify(mockRegime),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.goto("/technicals");
  });

  test("renders Market Regime section", async ({ page }) => {
    await expect(page.getByText("Market Regime")).toBeVisible();
  });

  test("renders regime value", async ({ page }) => {
    await expect(page.getByText("UPTREND")).toBeVisible();
  });

  test("renders Technical Indicators section", async ({ page }) => {
    await expect(page.getByText("Technical Indicators")).toBeVisible();
  });

  test("renders ticker in table", async ({ page }) => {
    await expect(page.getByText("SPY")).toBeVisible();
  });

  test("renders Refresh button", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();
  });

  test("refreshes data on Refresh click", async ({ page }) => {
    let callCount = 0;
    await page.route("**/api/technicals", (route) => {
      callCount++;
      route.fulfill({
        body: JSON.stringify(mockTechnicals),
        contentType: "application/json",
        status: 200,
      });
    });

    await page.getByRole("button", { name: "Refresh" }).click();
    // After click, technicals should be re-fetched (callCount > initial)
    expect(callCount).toBeGreaterThan(0);
  });
});
