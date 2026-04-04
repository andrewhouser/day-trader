import { expect, test } from "@playwright/test";

const mockTrades = [
  {
    close_date: "2026-01-15",
    close_price: 510.0,
    entry_date: "2026-01-01",
    entry_price: 490.0,
    instrument_type: "ETF",
    pnl: 200.0,
    quantity: 10,
    reason: "Target reached",
    ticker: "SPY",
  },
  {
    close_date: "2026-01-20",
    close_price: 85.0,
    entry_date: "2026-01-10",
    entry_price: 87.0,
    instrument_type: "ETF",
    pnl: -20.0,
    quantity: 10,
    reason: "Stop triggered",
    ticker: "EWJ",
  },
];

test.describe("Trades", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/trades*", (route) =>
      route.fulfill({
        body: JSON.stringify(mockTrades),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.goto("/trades");
  });

  test("renders trade tickers", async ({ page }) => {
    await expect(page.getByText("SPY")).toBeVisible();
    await expect(page.getByText("EWJ")).toBeVisible();
  });

  test("renders positive PnL", async ({ page }) => {
    await expect(page.getByText(/\+\$200/)).toBeVisible();
  });

  test("renders negative PnL", async ({ page }) => {
    await expect(page.getByText(/-\$20/)).toBeVisible();
  });

  test("renders close reasons", async ({ page }) => {
    await expect(page.getByText("Target reached")).toBeVisible();
  });
});
