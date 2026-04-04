import { expect, test } from "@playwright/test";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept API calls with mock data
    await page.route("**/api/portfolio", (route) =>
      route.fulfill({
        body: JSON.stringify({
          all_time_high: 110000,
          all_time_low: 95000,
          cash_usd: 20000,
          last_updated: "2026-01-01T10:00:00Z",
          positions: [
            {
              current_price: 505,
              entry_date: "2025-12-01T09:00:00Z",
              entry_price: 490,
              instrument_type: "ETF",
              notes: "Momentum trade",
              quantity: 10,
              ticker: "SPY",
              trailing_stop: 480,
            },
          ],
          starting_capital: 100000,
          total_value_usd: 105000,
          trade_count: 5,
        }),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.route("**/api/tasks", (route) =>
      route.fulfill({
        body: JSON.stringify([]),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.goto("/");
  });

  test("renders portfolio stats", async ({ page }) => {
    await expect(page.getByText(/Portfolio Value/)).toBeVisible();
  });

  test("renders position rows", async ({ page }) => {
    await expect(page.getByText("SPY")).toBeVisible();
  });

  test("renders cash balance", async ({ page }) => {
    await expect(page.getByText(/Cash/)).toBeVisible();
  });
});
