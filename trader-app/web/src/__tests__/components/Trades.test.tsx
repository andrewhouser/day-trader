import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Trades } from "@/components/Trades";

const mockTrades = [
  {
    action: "BUY",
    date: "2026-01-01",
    instrument: "SPY",
    portfolio_balance: "$102,000",
    price: "$500.00",
    quantity: "10",
    raw: "BUY 10 SPY @ $500",
    realized_pnl: "+$500",
    reasoning: "Strong uptrend momentum",
  },
  {
    action: "SELL",
    date: "2026-01-02",
    instrument: "QQQ",
    portfolio_balance: "$103,000",
    price: "$400.00",
    quantity: "5",
    raw: "SELL 5 QQQ @ $400",
    realized_pnl: "-$200",
    reasoning: "Resistance level hit",
  },
  {
    action: "NO_ACTION",
    date: "2026-01-03",
    instrument: undefined,
    portfolio_balance: "$103,000",
    price: undefined,
    quantity: undefined,
    raw: "No action taken today",
    realized_pnl: undefined,
    reasoning: "Awaiting confirmation",
  },
];

vi.mock("@/lib/api", () => ({
  api: {
    getTrades: vi.fn().mockResolvedValue(mockTrades),
  },
}));

describe("Trades", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Trades />);
    expect(screen.getByText(/Loading trades/)).toBeInTheDocument();
  });

  it("renders trade log title with count", async () => {
    render(<Trades />);
    expect(await screen.findByText("Trade Log (3 entries)")).toBeInTheDocument();
  });

  it("renders BUY badge", async () => {
    render(<Trades />);
    await screen.findByText("BUY");
    expect(screen.getByText("BUY")).toBeInTheDocument();
  });

  it("renders SELL badge", async () => {
    render(<Trades />);
    await screen.findByText("SELL");
    expect(screen.getByText("SELL")).toBeInTheDocument();
  });

  it("renders HOLD badge for NO_ACTION", async () => {
    render(<Trades />);
    await screen.findByText("HOLD");
    expect(screen.getByText("HOLD")).toBeInTheDocument();
  });

  it("renders table headers", async () => {
    render(<Trades />);
    await screen.findByText("Date");
    expect(screen.getByText("Action")).toBeInTheDocument();
    expect(screen.getByText("Instrument")).toBeInTheDocument();
    expect(screen.getByText("Price")).toBeInTheDocument();
  });

  it("expands row to show reasoning on click", async () => {
    const user = userEvent.setup();
    render(<Trades />);
    await screen.findByText("SPY");

    const rows = screen.getAllByRole("button");
    await user.click(rows[0]);

    expect(await screen.findByText("Strong uptrend momentum")).toBeInTheDocument();
  });

  it("shows empty state when no trades", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getTrades).mockResolvedValue([]);

    render(<Trades />);
    expect(await screen.findByText("No trades recorded yet.")).toBeInTheDocument();
  });
});
