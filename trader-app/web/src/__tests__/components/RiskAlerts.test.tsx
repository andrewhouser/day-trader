import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RiskAlerts } from "@/components/RiskAlerts";

const mockAlerts = [
  {
    raw: "## Risk Alert - 2026-01-03 09:12:06\n⚡ VOLATILITY: EWJ intraday range 5.21% (H: $85.84 L: $81.43)\n⚡ VOLATILITY: SPY intraday range 2.10% (H: $502.00 L: $491.50)",
  },
  {
    raw: "## Risk Alert - 2026-01-02 14:30:00\nMarket conditions stable.",
  },
];

vi.mock("@/lib/api", () => ({
  api: {
    getRiskAlerts: vi.fn().mockResolvedValue(mockAlerts),
  },
}));

describe("RiskAlerts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<RiskAlerts />);
    expect(screen.getByText(/Loading risk alerts/)).toBeInTheDocument();
  });

  it("renders alert count", async () => {
    render(<RiskAlerts />);
    expect(await screen.findByText("Risk Alerts (2)")).toBeInTheDocument();
  });

  it("renders parsed ticker volatility entries", async () => {
    render(<RiskAlerts />);
    await screen.findByText("EWJ");
    expect(screen.getByText("SPY")).toBeInTheDocument();
  });

  it("renders intraday range percentages", async () => {
    render(<RiskAlerts />);
    await screen.findByText("5.21%");
    expect(screen.getByText("2.10%")).toBeInTheDocument();
  });

  it("shows high/low values", async () => {
    render(<RiskAlerts />);
    await screen.findByText("$85.84");
    expect(screen.getByText("$81.43")).toBeInTheDocument();
  });

  it("renders other alert lines", async () => {
    render(<RiskAlerts />);
    await screen.findByText("Market conditions stable.");
  });

  it("shows empty state when no alerts", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getRiskAlerts).mockResolvedValue([]);

    render(<RiskAlerts />);
    expect(await screen.findByText(/No risk alerts/)).toBeInTheDocument();
  });
});
