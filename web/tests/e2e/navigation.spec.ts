import { expect, test } from "@playwright/test";

test.describe("Navigation", () => {
  test("loads the home page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Day Trader/);
  });

  test("renders the nav sidebar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test("navigates to Tasks page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Tasks" }).click();
    await expect(page).toHaveURL("/tasks");
  });

  test("navigates to Trades page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Trades" }).click();
    await expect(page).toHaveURL("/trades");
  });

  test("navigates to Technicals page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Technicals" }).click();
    await expect(page).toHaveURL("/technicals");
  });

  test("navigates to Expansion page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Expansion" }).click();
    await expect(page).toHaveURL("/expansion");
  });

  test("navigates to Research page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Research" }).click();
    await expect(page).toHaveURL("/research");
  });

  test("navigates to Sentiment page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Sentiment" }).click();
    await expect(page).toHaveURL("/sentiment");
  });

  test("navigates to News page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "News" }).click();
    await expect(page).toHaveURL("/news");
  });

  test("navigates to Events page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Events" }).click();
    await expect(page).toHaveURL("/events");
  });

  test("navigates to Performance page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Performance" }).click();
    await expect(page).toHaveURL("/performance");
  });

  test("navigates to Reports page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Reports" }).click();
    await expect(page).toHaveURL("/reports");
  });

  test("navigates to Reflections page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Reflections" }).click();
    await expect(page).toHaveURL("/reflections");
  });

  test("navigates to Risk page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Risk" }).click();
    await expect(page).toHaveURL("/risk");
  });

  test("navigates to Chat page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Chat" }).click();
    await expect(page).toHaveURL("/chat");
  });

  test("active nav link is highlighted for current route", async ({ page }) => {
    await page.goto("/tasks");
    const tasksLink = page.getByRole("link", { name: "Tasks" });
    // active link has a distinct style (navLinkActive class)
    await expect(tasksLink).toHaveClass(/navLinkActive/);
  });
});
