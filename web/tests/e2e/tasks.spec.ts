import { expect, test } from "@playwright/test";

const mockTasks = [
  {
    description: "Runs daily market analysis",
    last_run: "2026-01-01T08:00:00Z",
    name: "market_analysis",
    schedule: "0 8 * * 1-5",
    status: "IDLE",
    task_id: "task-1",
  },
  {
    description: "Monitors positions and risk",
    last_run: null,
    name: "risk_monitor",
    schedule: null,
    status: "IDLE",
    task_id: "task-2",
  },
];

test.describe("Tasks", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/tasks", (route) =>
      route.fulfill({
        body: JSON.stringify(mockTasks),
        contentType: "application/json",
        status: 200,
      })
    );
    await page.goto("/tasks");
  });

  test("renders task names", async ({ page }) => {
    await expect(page.getByText("market_analysis")).toBeVisible();
    await expect(page.getByText("risk_monitor")).toBeVisible();
  });

  test("renders Run buttons", async ({ page }) => {
    const runButtons = page.getByRole("button", { name: "Run" });
    await expect(runButtons.first()).toBeVisible();
  });

  test("triggers task run on Run button click", async ({ page }) => {
    let ranTaskId = "";

    await page.route("**/api/tasks/task-1/run", (route) => {
      ranTaskId = "task-1";
      route.fulfill({
        body: JSON.stringify({ task_id: "task-1", status: "RUNNING" }),
        contentType: "application/json",
        status: 200,
      });
    });

    // Re-route tasks to return one RUNNING task after run
    await page.route("**/api/tasks", (route) => {
      if (ranTaskId === "task-1") {
        route.fulfill({
          body: JSON.stringify([{ ...mockTasks[0], status: "RUNNING" }, mockTasks[1]]),
          contentType: "application/json",
          status: 200,
        });
      } else {
        route.fulfill({
          body: JSON.stringify(mockTasks),
          contentType: "application/json",
          status: 200,
        });
      }
    });

    const runButtons = page.getByRole("button", { name: "Run" });
    await runButtons.first().click();

    await expect(page.getByText("Stop")).toBeVisible();
  });

  test("renders schedule for tasks with cron", async ({ page }) => {
    await expect(page.getByText(/0 8 \* \* 1-5/)).toBeVisible();
  });
});
