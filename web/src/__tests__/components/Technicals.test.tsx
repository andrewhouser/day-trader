import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Technicals } from "@/components/Technicals";

const mockTechnicals = {
  EWJ: {
    atr_14: "1.23",
    bb_lower: "82.10",
    bb_upper: "87.50",
    macd_histogram: 0.45,
    price: "85.20",
    roc_20: "2.3",
    rsi_14: 55.2,
    sma_20: "84.50",
    sma_200: "80.00",
    sma_50: "83.20",
    volume_ratio: "1.2",
  },
  SPY: {
    atr_14: "8.50",
    bb_lower: "490.00",
    bb_upper: "520.00",
    macd_histogram: -0.32,
    price: "500.00",
    roc_20: "-1.5",
    rsi_14: 72.1,
    sma_20: "498.00",
    sma_200: "470.00",
    sma_50: "495.00",
    volume_ratio: "0.9",
  },
};

const mockRegime = {
  parameters: { strategy_note: "Use momentum strategies" },
  regime: "UPTREND",
  signals: { golden_cross: true, roc_20: 2.3, rsi: 55, vix: 18.5 },
  timestamp: "2026-01-01T10:00:00Z",
};

vi.mock("@/lib/api", () => ({
  api: {
    getRegime: vi.fn().mockResolvedValue(mockRegime),
    getTechnicals: vi.fn().mockResolvedValue(mockTechnicals),
  },
}));

describe("Technicals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Technicals />);
    expect(screen.getByText(/Loading technicals/)).toBeInTheDocument();
  });

  it("renders market regime section", async () => {
    render(<Technicals />);
    expect(await screen.findByText("Market Regime")).toBeInTheDocument();
    expect(screen.getByText("UPTREND")).toBeInTheDocument();
  });

  it("renders strategy note from regime parameters", async () => {
    render(<Technicals />);
    await screen.findByText("Market Regime");
    expect(screen.getByText("Use momentum strategies")).toBeInTheDocument();
  });

  it("renders Technical Indicators section", async () => {
    render(<Technicals />);
    expect(await screen.findByText("Technical Indicators")).toBeInTheDocument();
  });

  it("renders ticker rows", async () => {
    render(<Technicals />);
    await screen.findByText("Technical Indicators");
    expect(screen.getByText("SPY")).toBeInTheDocument();
    expect(screen.getByText("EWJ")).toBeInTheDocument();
  });

  it("renders column headers with tooltips", async () => {
    render(<Technicals />);
    await screen.findByText("Technical Indicators");
    expect(screen.getByText("RSI")).toBeInTheDocument();
  });

  it("has a Refresh button", async () => {
    render(<Technicals />);
    await screen.findByText("Refresh");
  });

  it("refreshes data when Refresh is clicked", async () => {
    const user = userEvent.setup();
    render(<Technicals />);

    await screen.findByText("Refresh");
    const { api } = await import("@/lib/api");
    vi.mocked(api.getTechnicals).mockClear();

    await user.click(screen.getByText("Refresh"));
    expect(api.getTechnicals).toHaveBeenCalled();
  });

  it("shows error state when API fails", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getTechnicals).mockRejectedValue(new Error("Failed to fetch"));

    render(<Technicals />);
    expect(await screen.findByText(/Failed to fetch/)).toBeInTheDocument();
  });
});
