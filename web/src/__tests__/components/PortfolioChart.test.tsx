import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PortfolioChart } from "@/components/PortfolioChart";

const mockSnapshots = [
  { cash_usd: 20000, timestamp: "2026-01-01T09:00:00Z", total_value_usd: 100000 },
  { cash_usd: 19500, timestamp: "2026-01-15T09:00:00Z", total_value_usd: 102000 },
  { cash_usd: 21000, timestamp: "2026-01-30T09:00:00Z", total_value_usd: 104500 },
];

vi.mock("@/lib/api", () => ({
  api: {
    getPortfolioHistory: vi.fn().mockResolvedValue(mockSnapshots),
  },
}));

describe("PortfolioChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<PortfolioChart />);
    expect(screen.getByText(/Loading chart/)).toBeInTheDocument();
  });

  it("renders Portfolio History section title", async () => {
    render(<PortfolioChart />);
    expect(await screen.findByText("Portfolio History")).toBeInTheDocument();
  });

  it("renders range buttons", async () => {
    render(<PortfolioChart />);
    await screen.findByText("Portfolio History");
    expect(screen.getByText("1D")).toBeInTheDocument();
    expect(screen.getByText("7D")).toBeInTheDocument();
    expect(screen.getByText("1M")).toBeInTheDocument();
    expect(screen.getByText("3M")).toBeInTheDocument();
    expect(screen.getByText("6M")).toBeInTheDocument();
    expect(screen.getByText("1Y")).toBeInTheDocument();
  });

  it("renders data points label", async () => {
    render(<PortfolioChart />);
    expect(await screen.findByText("3 data points")).toBeInTheDocument();
  });

  it("shows empty state when no data", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getPortfolioHistory).mockResolvedValue([]);

    render(<PortfolioChart />);
    expect(await screen.findByText(/No history data for the/)).toBeInTheDocument();
  });

  it("changes range when range button clicked", async () => {
    const user = userEvent.setup();
    const { api } = await import("@/lib/api");

    render(<PortfolioChart />);
    await screen.findByText("Portfolio History");

    vi.mocked(api.getPortfolioHistory).mockClear();
    await user.click(screen.getByText("7D"));

    expect(api.getPortfolioHistory).toHaveBeenCalledWith(7);
  });
});
