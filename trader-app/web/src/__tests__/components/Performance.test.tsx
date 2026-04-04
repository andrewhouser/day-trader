import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Performance } from "@/components/Performance";

const mockEntries = [
  { raw: "# Performance Report\n\nWin rate: 65%\nNet P&L: +$2,500" },
];

const mockWeights = {
  defaults: { momentum: 1.0, sentiment: 1.0, trend: 1.0 },
  weights: {
    SPY: { event_risk: 0.8, momentum: 1.2, risk_reward: 1.0, sector_divergence: 1.0, sentiment: 0.9, trend: 1.1 },
  },
};

vi.mock("@/lib/api", () => ({
  api: {
    getPerformance: vi.fn().mockResolvedValue(mockEntries),
    getScoreWeights: vi.fn().mockResolvedValue(mockWeights),
  },
}));

describe("Performance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Performance />);
    expect(screen.getByText(/Loading performance/)).toBeInTheDocument();
  });

  it("renders Score Dimension Weights section", async () => {
    render(<Performance />);
    expect(await screen.findByText("Score Dimension Weights")).toBeInTheDocument();
  });

  it("renders ticker row in weights table", async () => {
    render(<Performance />);
    await screen.findByText("Score Dimension Weights");
    expect(screen.getByText("SPY")).toBeInTheDocument();
  });

  it("renders dimension columns", async () => {
    render(<Performance />);
    await screen.findByText("Score Dimension Weights");
    expect(screen.getByText("trend")).toBeInTheDocument();
    expect(screen.getByText("momentum")).toBeInTheDocument();
    expect(screen.getByText("sentiment")).toBeInTheDocument();
  });

  it("renders Performance Reports section", async () => {
    render(<Performance />);
    expect(await screen.findByText(/Performance Reports \(1\)/)).toBeInTheDocument();
  });

  it("renders report content", async () => {
    render(<Performance />);
    await screen.findByText(/Win rate: 65%/);
  });

  it("shows empty reports state", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getPerformance).mockResolvedValue([]);

    render(<Performance />);
    expect(
      await screen.findByText(/No performance reports yet/)
    ).toBeInTheDocument();
  });
});
