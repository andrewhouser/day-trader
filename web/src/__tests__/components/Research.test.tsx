import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Research } from "@/components/Research";

vi.mock("@/lib/api", () => ({
  api: {
    getResearch: vi.fn().mockResolvedValue([
      { raw: "# Research Note\n\nSPY showing bullish momentum." },
      { raw: "# Research Note\n\nBond yields stabilizing." },
    ]),
  },
}));

describe("Research", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Research />);
    expect(screen.getByText(/Loading research/)).toBeInTheDocument();
  });

  it("renders research count", async () => {
    render(<Research />);
    expect(await screen.findByText("Research Notes (2)")).toBeInTheDocument();
  });

  it("renders research content", async () => {
    render(<Research />);
    expect(await screen.findByText(/SPY showing bullish momentum/)).toBeInTheDocument();
  });

  it("shows empty state when no research", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getResearch).mockResolvedValue([]);

    render(<Research />);
    expect(await screen.findByText(/No research notes yet/)).toBeInTheDocument();
  });
});
