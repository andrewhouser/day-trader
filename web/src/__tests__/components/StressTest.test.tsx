import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StressTest } from "@/components/StressTest";

const mockResult = {
  current_portfolio_value: 100000,
  scenarios: [
    {
      description: "Equity markets drop 20%",
      forced_reduction_cost: null,
      name: "Bear Market",
      pct_change: -18.5,
      positions_oversized: [],
      positions_stopped_out: [
        { estimated_loss: 500, stop_type: "trailing_stop", ticker: "SPY" },
      ],
      shocked_value: 81500,
      summary: "Portfolio would lose $18,500 in a bear market scenario.",
    },
    {
      description: "Equity markets rally 15%",
      forced_reduction_cost: null,
      name: "Bull Run",
      pct_change: 12.3,
      positions_oversized: [],
      positions_stopped_out: [],
      shocked_value: 112300,
      summary: "Portfolio would gain $12,300 in a bull run.",
    },
  ],
  timestamp: "2026-01-01T10:00:00Z",
};

vi.mock("@/lib/api", () => ({
  api: {
    getStressTest: vi.fn().mockResolvedValue(mockResult),
  },
}));

describe("StressTest", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<StressTest />);
    expect(screen.getByText(/Running stress scenarios/)).toBeInTheDocument();
  });

  it("renders section title", async () => {
    render(<StressTest />);
    expect(await screen.findByText("Portfolio Stress Scenarios")).toBeInTheDocument();
  });

  it("renders scenario cards", async () => {
    render(<StressTest />);
    await screen.findByText("Bear Market");
    expect(screen.getByText("Bull Run")).toBeInTheDocument();
  });

  it("renders pct change badges", async () => {
    render(<StressTest />);
    await screen.findByText("-18.5%");
    expect(screen.getByText("+12.3%")).toBeInTheDocument();
  });

  it("renders stopped-out positions", async () => {
    render(<StressTest />);
    await screen.findByText("Positions Stopped Out");
    expect(screen.getByText("SPY")).toBeInTheDocument();
  });

  it("renders summaries", async () => {
    render(<StressTest />);
    await screen.findByText(/Portfolio would lose \$18,500/);
  });

  it("has a Re-run button", async () => {
    render(<StressTest />);
    await screen.findByText("Portfolio Stress Scenarios");
    expect(screen.getByText("Re-run")).toBeInTheDocument();
  });

  it("re-runs stress test when Re-run is clicked", async () => {
    const user = userEvent.setup();
    render(<StressTest />);

    await screen.findByText("Re-run");
    const { api } = await import("@/lib/api");
    vi.mocked(api.getStressTest).mockClear();

    await user.click(screen.getByText("Re-run"));

    expect(api.getStressTest).toHaveBeenCalled();
  });
});
