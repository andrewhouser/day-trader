import { expect, test } from "@playwright/test";

test.describe("Chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat");
  });

  test("renders chat welcome message", async ({ page }) => {
    await expect(page.getByText(/Ask me anything/)).toBeVisible();
  });

  test("renders message input", async ({ page }) => {
    await expect(page.getByRole("textbox")).toBeVisible();
  });

  test("renders send button", async ({ page }) => {
    await expect(page.getByRole("button", { name: /Send/ })).toBeVisible();
  });

  test("send button is disabled when input is empty", async ({ page }) => {
    const sendButton = page.getByRole("button", { name: /Send/ });
    await expect(sendButton).toBeDisabled();
  });

  test("send button is enabled when input has text", async ({ page }) => {
    await page.getByRole("textbox").fill("What is the market doing?");
    const sendButton = page.getByRole("button", { name: /Send/ });
    await expect(sendButton).toBeEnabled();
  });

  test("sends message and displays user message", async ({ page }) => {
    await page.route("**/api/chat", (route) =>
      route.fulfill({
        body: JSON.stringify({ response: "The market is trending upward." }),
        contentType: "application/json",
        status: 200,
      })
    );

    const input = page.getByRole("textbox");
    await input.fill("What is the market doing?");
    await page.getByRole("button", { name: /Send/ }).click();

    await expect(page.getByText("What is the market doing?")).toBeVisible();
  });

  test("displays assistant response after send", async ({ page }) => {
    await page.route("**/api/chat", (route) =>
      route.fulfill({
        body: JSON.stringify({ response: "The market is trending upward." }),
        contentType: "application/json",
        status: 200,
      })
    );

    await page.getByRole("textbox").fill("What is the market doing?");
    await page.getByRole("button", { name: /Send/ }).click();

    await expect(page.getByText("The market is trending upward.")).toBeVisible();
  });
});
