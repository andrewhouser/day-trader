import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScenarioCard } from "@/components/ScenarioCard";
import { StressScenario } from "@/lib/api";

const bearScenario: StressScenario = {
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
};

const bullScenario: StressScenario = {
  description: "Equity markets rally 15%",
  forced_reduction_cost: null,
  name: "Bull Run",
  pct_change: 12.3,
  positions_oversized: [],
  positions_stopped_out: [],
  shocked_value: 112300,
  summary: "Portfolio would gain $12,300 in a bull run.",
};

describe("ScenarioCard", () => {
  it("renders scenario name", () => {
    render(<ScenarioCard currentValue={100000} scenario={bearScenario} />);
    expect(screen.getByText("Bear Market")).toBeInTheDocument();
  });

  it("renders scenario description", () => {
    render(<ScenarioCard currentValue={100000} scenario={bearScenario} />);
    expect(screen.getByText("Equity markets drop 20%")).toBeInTheDocument();
  });

  it("renders negative pct change badge", () => {
    render(<ScenarioCard currentValue={100000} scenario={bearScenario} />);
    expect(screen.getByText("-18.5%")).toBeInTheDocument();
  });

  it("renders positive pct change badge with + prefix", () => {
    render(<ScenarioCard currentValue={100000} scenario={bullScenario} />);
    expect(screen.getByText("+12.3%")).toBeInTheDocument();
  });

  it("renders current and shocked values", () => {
    render(<ScenarioCard currentValue={100000} scenario={bearScenario} />);
    expect(screen.getByText(/Current:/)).toBeInTheDocument();
    expect(screen.getByText(/Shocked:/)).toBeInTheDocument();
  });

  it("renders stopped-out positions table when present", () => {
    render(<ScenarioCard currentValue={100000} scenario={bearScenario} />);
    expect(screen.getByText("Positions Stopped Out")).toBeInTheDocument();
    expect(screen.getByText("SPY")).toBeInTheDocument();
    expect(screen.getByText("trailing stop")).toBeInTheDocument();
    expect(screen.getByText("$500.00")).toBeInTheDocument();
  });

  it("does not render stopped-out section when empty", () => {
    render(<ScenarioCard currentValue={100000} scenario={bullScenario} />);
    expect(screen.queryByText("Positions Stopped Out")).not.toBeInTheDocument();
  });

  it("renders summary", () => {
    render(<ScenarioCard currentValue={100000} scenario={bearScenario} />);
    expect(screen.getByText(/Portfolio would lose \$18,500/)).toBeInTheDocument();
  });

  it("renders oversized positions when present", () => {
    const withOversized: StressScenario = {
      ...bullScenario,
      forced_reduction_cost: 250.0,
      positions_oversized: [{ current_pct: 35.5, ticker: "QQQ" }],
    };
    render(<ScenarioCard currentValue={100000} scenario={withOversized} />);
    expect(screen.getByText("Oversized Positions")).toBeInTheDocument();
    expect(screen.getByText("QQQ")).toBeInTheDocument();
    expect(screen.getByText(/Estimated forced reduction/)).toBeInTheDocument();
  });
});
