import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Reflections } from "@/components/Reflections";

vi.mock("@/lib/api", () => ({
  api: {
    getReflections: vi.fn().mockResolvedValue([
      { raw: "# Trade Reflection\n\nSPY trade closed with +2.5% gain." },
      { raw: "# Trade Reflection\n\nEWJ position stopped out at breakeven." },
    ]),
  },
}));

describe("Reflections", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Reflections />);
    expect(screen.getByText(/Loading reflections/)).toBeInTheDocument();
  });

  it("renders reflection count", async () => {
    render(<Reflections />);
    expect(await screen.findByText("Agent Reflections (2)")).toBeInTheDocument();
  });

  it("renders reflection content", async () => {
    render(<Reflections />);
    expect(await screen.findByText(/SPY trade closed/)).toBeInTheDocument();
  });

  it("shows empty state when no reflections", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getReflections).mockResolvedValue([]);

    render(<Reflections />);
    expect(
      await screen.findByText(/No reflections yet/)
    ).toBeInTheDocument();
  });
});
