import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PositionChart } from "@/components/PositionChart";

const mockSnapshots = [
  { high: 505, low: 495, price: 500, time: "2026-01-01T09:00:00Z" },
  { high: 508, low: 498, price: 503, time: "2026-01-15T09:00:00Z" },
  { high: 512, low: 504, price: 510, time: "2026-01-30T09:00:00Z" },
];

vi.mock("@/lib/api", () => ({
  api: {
    getTickerHistory: vi.fn().mockResolvedValue(mockSnapshots),
  },
}));

describe("PositionChart", () => {
  const defaultProps = {
    entryPrice: 490.0,
    onClose: vi.fn(),
    ticker: "SPY",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<PositionChart {...defaultProps} />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("renders ticker title", async () => {
    render(<PositionChart {...defaultProps} />);
    expect(await screen.findByText("SPY Price History")).toBeInTheDocument();
  });

  it("renders range buttons", async () => {
    render(<PositionChart {...defaultProps} />);
    await screen.findByText("SPY Price History");
    expect(screen.getByText("1D")).toBeInTheDocument();
    expect(screen.getByText("1M")).toBeInTheDocument();
    expect(screen.getByText("1Y")).toBeInTheDocument();
  });

  it("renders close button", async () => {
    render(<PositionChart {...defaultProps} />);
    await screen.findByText("SPY Price History");
    expect(screen.getByLabelText("Close")).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<PositionChart {...defaultProps} onClose={onClose} />);

    await screen.findByText("SPY Price History");
    await user.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when overlay clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<PositionChart {...defaultProps} onClose={onClose} />);

    await screen.findByText("SPY Price History");
    // Click the overlay (modal-overlay div) not the inner content
    const overlay = document.querySelector(".modal-overlay") as HTMLElement;
    await user.click(overlay);
    expect(onClose).toHaveBeenCalled();
  });

  it("renders data points label", async () => {
    render(<PositionChart {...defaultProps} />);
    expect(await screen.findByText("3 data points")).toBeInTheDocument();
  });

  it("shows empty state when no data", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getTickerHistory).mockResolvedValue([]);

    render(<PositionChart {...defaultProps} />);
    expect(await screen.findByText("No data available")).toBeInTheDocument();
  });

  it("shows error state when API fails", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getTickerHistory).mockRejectedValue(new Error("Network error"));

    render(<PositionChart {...defaultProps} />);
    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });

  it("changes range when range button clicked", async () => {
    const user = userEvent.setup();
    const { api } = await import("@/lib/api");

    render(<PositionChart {...defaultProps} />);
    await screen.findByText("SPY Price History");

    vi.mocked(api.getTickerHistory).mockClear();
    await user.click(screen.getByText("7D"));

    expect(api.getTickerHistory).toHaveBeenCalledWith("SPY", 7);
  });
});
