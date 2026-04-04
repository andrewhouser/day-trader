import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ScheduleEditor } from "@/components/ScheduleEditor";

const defaultProps = {
  currentCron: "0 7 * * 1-5",
  onClose: vi.fn(),
  onSave: vi.fn().mockResolvedValue(undefined),
  taskId: "trader",
  taskName: "Trader",
};

describe("ScheduleEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the modal with task name", () => {
    render(<ScheduleEditor {...defaultProps} />);
    expect(screen.getByText("Edit Schedule: Trader")).toBeInTheDocument();
  });

  it("renders frequency selector", () => {
    render(<ScheduleEditor {...defaultProps} />);
    expect(screen.getByLabelText("Frequency")).toBeInTheDocument();
  });

  it("renders day picker buttons", () => {
    render(<ScheduleEditor {...defaultProps} />);
    expect(screen.getByText("Mon")).toBeInTheDocument();
    expect(screen.getByText("Fri")).toBeInTheDocument();
    expect(screen.getByText("Sat")).toBeInTheDocument();
  });

  it("renders Save Schedule and Cancel buttons", () => {
    render(<ScheduleEditor {...defaultProps} />);
    expect(screen.getByText("Save Schedule")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("calls onClose when Cancel is clicked", async () => {
    const user = userEvent.setup();
    render(<ScheduleEditor {...defaultProps} />);

    await user.click(screen.getByText("Cancel"));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("calls onSave with taskId and cron when Save is clicked", async () => {
    const user = userEvent.setup();
    render(<ScheduleEditor {...defaultProps} />);

    await user.click(screen.getByText("Save Schedule"));
    expect(defaultProps.onSave).toHaveBeenCalledWith("trader", expect.any(String));
  });

  it("closes when overlay is clicked", async () => {
    const user = userEvent.setup();
    const { container } = render(<ScheduleEditor {...defaultProps} />);

    const overlay = container.querySelector('[role="dialog"]');
    if (overlay) await user.click(overlay);

    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("shows preview of schedule", () => {
    render(<ScheduleEditor {...defaultProps} />);
    expect(screen.getByText("Preview")).toBeInTheDocument();
  });

  it("shows every N minutes options when frequency changes", async () => {
    const user = userEvent.setup();
    render(<ScheduleEditor {...defaultProps} />);

    const select = screen.getByLabelText("Frequency");
    await user.selectOptions(select, "every_n_min");

    expect(screen.getByText("minutes")).toBeInTheDocument();
  });
});
