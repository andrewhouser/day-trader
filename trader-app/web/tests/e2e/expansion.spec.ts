import { expect, test } from "@playwright/test";

const mockProposals = [
  {
    created_at: "2026-01-01T10:00:00Z",
    description: "Strong momentum and bullish sentiment",
    expected_return: 0.05,
    instruments: [{ quantity: 5, ticker: "QQQ", type: "ETF" }],
    proposal_id: "prop-1",
    rationale: "Tech sector showing relative strength.",
    status: "pending",
    ticker: "QQQ",
  },
];

test.describe("Expansion", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/expansion/proposals", (route) =>
      route.fulfill({
        body: JSON.stringify(mockProposals),
        contentType: "application/json",
        status: 200,
      })
    );
    await page.goto("/expansion");
  });

  test("renders proposal ticker", async ({ page }) => {
    await expect(page.getByText("QQQ")).toBeVisible();
  });

  test("renders expected return", async ({ page }) => {
    await expect(page.getByText(/5\.0%/)).toBeVisible();
  });

  test("renders Approve and Reject buttons", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Approve" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reject" })).toBeVisible();
  });

  test("approves proposal on Approve click", async ({ page }) => {
    await page.route("**/api/expansion/proposals/prop-1/approve", (route) =>
      route.fulfill({
        body: JSON.stringify({ status: "approved" }),
        contentType: "application/json",
        status: 200,
      })
    );

    // After approval, return empty proposals list
    await page.route("**/api/expansion/proposals", (route) =>
      route.fulfill({
        body: JSON.stringify([]),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText(/No pending expansion proposals/)).toBeVisible();
  });

  test("shows empty state when no proposals", async ({ page }) => {
    await page.route("**/api/expansion/proposals", (route) =>
      route.fulfill({
        body: JSON.stringify([]),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.goto("/expansion");
    await expect(page.getByText(/No pending expansion proposals/)).toBeVisible();
  });
});
