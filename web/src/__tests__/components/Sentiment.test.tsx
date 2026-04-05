import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Sentiment } from "@/components/Sentiment";

vi.mock("@/lib/api", () => ({
  api: {
    getSentiment: vi.fn().mockResolvedValue([
      { raw: "# Sentiment Analysis\n\nSPY: **Bullish** (score: 0.72)" },
    ]),
  },
}));

describe("Sentiment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Sentiment />);
    expect(screen.getByText(/Loading sentiment/)).toBeInTheDocument();
  });

  it("renders sentiment count", async () => {
    render(<Sentiment />);
    expect(await screen.findByText("Sentiment Analysis (1)")).toBeInTheDocument();
  });

  it("renders sentiment content", async () => {
    render(<Sentiment />);
    expect(await screen.findByText(/SPY/)).toBeInTheDocument();
  });

  it("shows empty state when no entries", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getSentiment).mockResolvedValue([]);

    render(<Sentiment />);
    expect(await screen.findByText(/No sentiment analysis yet/)).toBeInTheDocument();
  });
});
