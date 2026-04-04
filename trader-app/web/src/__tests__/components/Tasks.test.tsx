import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Tasks } from "@/components/Tasks";

const mockTasks = [
  {
    cron: "*/30 9-16 * * 1-5",
    is_running: false,
    last_run: null,
    name: "Trader",
    task_id: "trader",
  },
  {
    cron: "*/3 9-16 * * 1-5",
    is_running: true,
    last_run: {
      error: null,
      finished_at: null,
      started_at: "2026-01-01T10:00:00Z",
      status: "running",
      task_id: "risk_monitor",
      task_name: "Risk Monitor",
    },
    name: "Risk Monitor",
    task_id: "risk_monitor",
  },
];

const mockHistory = [
  {
    error: null,
    finished_at: "2026-01-01T10:05:00Z",
    started_at: "2026-01-01T10:00:00Z",
    status: "completed",
    task_id: "trader",
    task_name: "Trader",
  },
];

vi.mock("@/lib/api", () => ({
  api: {
    getTaskHistory: vi.fn().mockResolvedValue(mockHistory),
    getTasks: vi.fn().mockResolvedValue(mockTasks),
    runTask: vi.fn().mockResolvedValue({ status: "started" }),
    stopTask: vi.fn().mockResolvedValue({ status: "stopping" }),
    updateTaskSchedule: vi.fn().mockResolvedValue({ cron: "0 9 * * 1-5", task_id: "trader" }),
  },
}));

vi.mock("@/components/ScheduleEditor", () => ({
  ScheduleEditor: ({ taskName }: { taskName: string }) => (
    <div data-testid="schedule-editor">{taskName}</div>
  ),
}));

describe("Tasks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Tasks />);
    expect(screen.getByText(/Loading tasks/)).toBeInTheDocument();
  });

  it("renders task names after load", async () => {
    render(<Tasks />);
    expect(await screen.findByText("Trader")).toBeInTheDocument();
    expect(screen.getByText("Risk Monitor")).toBeInTheDocument();
  });

  it("shows running badge for active tasks", async () => {
    render(<Tasks />);
    await screen.findByText("Risk Monitor");
    expect(screen.getByText(/Running/)).toBeInTheDocument();
  });

  it("shows idle badge for inactive tasks", async () => {
    render(<Tasks />);
    await screen.findByText("Trader");
    expect(screen.getAllByText("Idle").length).toBeGreaterThan(0);
  });

  it("renders execution history", async () => {
    render(<Tasks />);
    await screen.findByText("Execution History");
    expect(screen.getByText("Trader", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("enables Run Now button for idle tasks", async () => {
    render(<Tasks />);
    await screen.findByText("Trader");
    const runButtons = screen.getAllByText("▶ Run Now");
    const idleButton = runButtons.find((btn) => !btn.closest("button")?.disabled);
    expect(idleButton).toBeDefined();
  });

  it("enables Stop button for running tasks", async () => {
    render(<Tasks />);
    await screen.findByText("Risk Monitor");
    const stopButtons = screen.getAllByText("■ Stop");
    const activeStop = stopButtons.find((btn) => !btn.closest("button")?.disabled);
    expect(activeStop).toBeDefined();
  });

  it("opens schedule editor when edit icon is clicked", async () => {
    const user = userEvent.setup();
    render(<Tasks />);
    await screen.findByText("Trader");

    const editButtons = screen.getAllByTitle("Edit schedule");
    await user.click(editButtons[0]);

    expect(screen.getByTestId("schedule-editor")).toBeInTheDocument();
  });
});
