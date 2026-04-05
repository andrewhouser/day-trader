import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Tip } from "@/components/Tip";

const tooltips = {
  RSI: "Relative Strength Index: measures momentum on a scale of 0-100.",
  SMA: "Simple Moving Average: average price over a period.",
};

describe("Tip", () => {
  it("renders the label text", () => {
    render(<Tip label="RSI" tooltips={tooltips} />);
    expect(screen.getByText("RSI")).toBeInTheDocument();
  });

  it("renders tooltip bubble text when tooltip exists", () => {
    render(<Tip label="RSI" tooltips={tooltips} />);
    expect(
      screen.getByText(/Relative Strength Index/)
    ).toBeInTheDocument();
  });

  it("renders plain text when no tooltip for label", () => {
    render(<Tip label="MACD" tooltips={tooltips} />);
    expect(screen.getByText("MACD")).toBeInTheDocument();
  });

  it("does not render bubble when no tooltip for label", () => {
    render(<Tip label="MACD" tooltips={tooltips} />);
    expect(screen.queryByText(/measures momentum/)).not.toBeInTheDocument();
  });
});
