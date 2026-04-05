import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IndexTracker } from "@/components/IndexTracker";

const mockIndices = {
  "S&P 500": { change: 12.5, change_pct: 0.32, price: 5200.5, symbol: "SPY" },
  NASDAQ: { change: -30.1, change_pct: -0.18, price: 16400.2, symbol: "QQQ" },
};

vi.mock("@/lib/api", () => ({
  api: {
    getIndices: vi.fn().mockResolvedValue(mockIndices),
  },
}));

describe("IndexTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing initially (returns null before data loads)", () => {
    const { container } = render(<IndexTracker />);
    expect(container.firstChild).toBeNull();
  });

  it("renders index names after data loads", async () => {
    render(<IndexTracker />);
    expect(await screen.findByText("S&P 500")).toBeInTheDocument();
    expect(screen.getByText("NASDAQ")).toBeInTheDocument();
  });

  it("renders positive change with up arrow", async () => {
    render(<IndexTracker />);
    await screen.findByText("S&P 500");
    const upIndicators = screen.getAllByText(/▲/);
    expect(upIndicators.length).toBeGreaterThan(0);
  });

  it("renders negative change with down arrow", async () => {
    render(<IndexTracker />);
    await screen.findByText("NASDAQ");
    const downIndicators = screen.getAllByText(/▼/);
    expect(downIndicators.length).toBeGreaterThan(0);
  });

  it("renders error state as dash", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getIndices).mockResolvedValue({
      "Bad Index": { error: "timeout", symbol: "BAD" },
    } as Record<string, unknown>);

    render(<IndexTracker />);
    await screen.findByText("Bad Index");
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
