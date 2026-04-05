import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { News } from "@/components/News";

const mockArticles = [
  {
    published: new Date(Date.now() - 3600000).toISOString(),
    related_query: "SPY ETF",
    source: "Reuters",
    tickers: ["SPY", "QQQ"],
    title: "Markets Rally on Fed Comments",
    url: "https://example.com/article1",
  },
  {
    published: new Date(Date.now() - 7200000).toISOString(),
    related_query: "AAPL stock",
    source: "Bloomberg",
    tickers: ["AAPL"],
    title: "Apple Reports Record Earnings",
    url: "https://example.com/article2",
  },
];

vi.mock("@/lib/api", () => ({
  api: {
    getNews: vi.fn().mockResolvedValue({ articles: mockArticles, timestamp: "2026-01-01" }),
  },
}));

describe("News", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<News />);
    expect(screen.getByText(/Loading news/)).toBeInTheDocument();
  });

  it("renders article titles", async () => {
    render(<News />);
    expect(await screen.findByText("Markets Rally on Fed Comments")).toBeInTheDocument();
    expect(screen.getByText("Apple Reports Record Earnings")).toBeInTheDocument();
  });

  it("renders article sources", async () => {
    render(<News />);
    await screen.findByText("Reuters");
    expect(screen.getByText("Bloomberg")).toBeInTheDocument();
  });

  it("renders ticker badges", async () => {
    render(<News />);
    await screen.findByText("SPY");
    expect(screen.getByText("QQQ")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });

  it("renders ticker filter buttons", async () => {
    render(<News />);
    await screen.findByText("Markets Rally on Fed Comments");
    expect(screen.getAllByText("SPY").length).toBeGreaterThan(0);
  });

  it("filters articles by ticker", async () => {
    const user = userEvent.setup();
    render(<News />);
    await screen.findByText("Markets Rally on Fed Comments");

    // Click AAPL filter button (in filter row, not badge in article)
    const filterButtons = screen.getAllByText("AAPL");
    await user.click(filterButtons[filterButtons.length - 1]);

    expect(screen.getByText("Apple Reports Record Earnings")).toBeInTheDocument();
    expect(screen.queryByText("Markets Rally on Fed Comments")).not.toBeInTheDocument();
  });

  it("renders All button to reset filter", async () => {
    render(<News />);
    await screen.findByText("Markets Rally on Fed Comments");
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
  });

  it("shows error when API fails", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getNews).mockRejectedValue(new Error("Network error"));

    render(<News />);
    expect(await screen.findByText(/Network error/)).toBeInTheDocument();
  });
});
