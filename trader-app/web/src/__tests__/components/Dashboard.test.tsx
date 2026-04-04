import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/components/Dashboard";

const mockPortfolio = {
  all_time_high: 105000,
  all_time_low: 95000,
  cash_usd: 50000,
  last_updated: "2026-01-01",
  positions: [
    {
      current_price: 220,
      entry_date: "2026-01-01",
      entry_price: 200,
      initial_stop: 190,
      instrument_type: "ETF",
      notes: "Test position",
      quantity: 10,
      take_profit_partial_hit: false,
      ticker: "SPY",
      trailing_stop: 195,
      unrealized_pnl: 200,
    },
  ],
  starting_capital: 100000,
  total_value_usd: 102000,
  trade_count: 5,
};

const mockTasks = [
  {
    cron: "0 */30 9-16 * * 1-5",
    is_running: false,
    last_run: null,
    name: "Trader",
    task_id: "trader",
  },
];

vi.mock("@/lib/api", () => ({
  api: {
    getPortfolio: vi.fn().mockResolvedValue(mockPortfolio),
    getRegime: vi.fn().mockResolvedValue({ parameters: {}, regime: "UPTREND", signals: {} }),
    getTasks: vi.fn().mockResolvedValue(mockTasks),
  },
}));

vi.mock("@/components/PortfolioChart", () => ({
  PortfolioChart: () => <div data-testid="portfolio-chart" />,
}));

vi.mock("@/components/PositionChart", () => ({
  PositionChart: () => <div data-testid="position-chart" />,
}));

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Dashboard />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("renders portfolio value after load", async () => {
    render(<Dashboard />);
    expect(await screen.findByText("Portfolio Value")).toBeInTheDocument();
    expect(screen.getByText(/102,000/)).toBeInTheDocument();
  });

  it("renders stat labels", async () => {
    render(<Dashboard />);
    await screen.findByText("Portfolio Value");
    expect(screen.getByText("Cash Available")).toBeInTheDocument();
    expect(screen.getByText("Total Return")).toBeInTheDocument();
    expect(screen.getByText("Market Regime")).toBeInTheDocument();
  });

  it("renders open positions table", async () => {
    render(<Dashboard />);
    await screen.findByText("Open Positions");
    expect(screen.getByText("SPY")).toBeInTheDocument();
    expect(screen.getByText("ETF")).toBeInTheDocument();
  });

  it("renders scheduled tasks table", async () => {
    render(<Dashboard />);
    await screen.findByText("Scheduled Tasks");
    expect(screen.getByText("Trader")).toBeInTheDocument();
  });

  it("renders the portfolio chart", async () => {
    render(<Dashboard />);
    await screen.findByTestId("portfolio-chart");
  });

  it("renders error state when API fails", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getPortfolio).mockRejectedValue(new Error("Network error"));

    render(<Dashboard />);
    expect(await screen.findByText(/Network error/)).toBeInTheDocument();
  });

  it("shows positive return styling", async () => {
    render(<Dashboard />);
    await screen.findByText("Total Return");
    expect(screen.getByText("+2.00%")).toBeInTheDocument();
  });
});
