import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Expansion } from "@/components/Expansion";

const mockProposals = [
  {
    category: "ETF",
    created_at: "2026-01-01T10:00:00Z",
    decided_at: null,
    description: "S&P 500 ETF tracking the largest US companies",
    expected_return: "8-10% annually",
    id: "1",
    instrument_type: "ETF",
    rationale: "Broad market exposure with low fees",
    region: "US",
    rejection_reason: null,
    risk_level: "low",
    source: "expansion_agent",
    status: "pending" as const,
    ticker: "VOO",
  },
];

const mockInstruments = {
  SPY: { tracks: "S&P 500", type: "ETF" },
};

vi.mock("@/lib/api", () => ({
  api: {
    approveProposal: vi.fn().mockResolvedValue({ status: "approved" }),
    getProposals: vi.fn().mockResolvedValue(mockProposals),
    getTradeableInstruments: vi.fn().mockResolvedValue(mockInstruments),
    rejectProposal: vi.fn().mockResolvedValue({ status: "rejected" }),
  },
}));

describe("Expansion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders tradeable instruments", async () => {
    render(<Expansion />);
    expect(await screen.findByText("Tradeable Instruments (1)")).toBeInTheDocument();
    expect(screen.getByText("SPY")).toBeInTheDocument();
  });

  it("renders filter buttons", async () => {
    render(<Expansion />);
    await screen.findByText("Tradeable Instruments (1)");
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  it("renders proposal details", async () => {
    render(<Expansion />);
    expect(await screen.findByText("VOO")).toBeInTheDocument();
    expect(screen.getByText("S&P 500 ETF tracking the largest US companies")).toBeInTheDocument();
    expect(screen.getByText(/Broad market exposure/)).toBeInTheDocument();
  });

  it("renders approve and reject buttons for pending proposals", async () => {
    render(<Expansion />);
    await screen.findByText("VOO");
    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
  });

  it("calls approveProposal when Approve is clicked", async () => {
    const user = userEvent.setup();
    render(<Expansion />);

    await screen.findByText("Approve");
    await user.click(screen.getByText("Approve"));

    const { api } = await import("@/lib/api");
    expect(api.approveProposal).toHaveBeenCalledWith("1");
  });
});
