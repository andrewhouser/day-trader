import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Nav } from "@/components/Nav";

vi.mock("@/lib/api", () => ({
  api: {
    getProposals: vi.fn().mockResolvedValue([]),
  },
}));

describe("Nav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders standalone tabs and group tabs", () => {
    render(<Nav />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Learn")).toBeInTheDocument();
    expect(screen.getByText("Trading")).toBeInTheDocument();
    expect(screen.getByText("Analysis")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText("System")).toBeInTheDocument();
  });

  it("shows sub-tabs inline for the active group", () => {
    const { usePathname } = vi.mocked(await import("next/navigation"));
    usePathname.mockReturnValue("/trades");

    render(<Nav />);
    // Trading sub-tabs should be visible
    expect(screen.getByText("Trades")).toBeInTheDocument();
    expect(screen.getByText("Expansion")).toBeInTheDocument();
    expect(screen.getByText("Research")).toBeInTheDocument();
    expect(screen.getByText("Technicals")).toBeInTheDocument();
  });

  it("marks the active sub-tab and group tab", () => {
    const { usePathname } = vi.mocked(await import("next/navigation"));
    usePathname.mockReturnValue("/trades");

    render(<Nav />);
    const tradesLink = screen.getByRole("tab", { name: "Trades" });
    expect(tradesLink).toHaveAttribute("aria-selected", "true");
    const tradingGroup = screen.getByRole("tab", { name: "Trading" });
    expect(tradingGroup).toHaveAttribute("aria-selected", "true");
  });

  it("has main navigation role", () => {
    render(<Nav />);
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("shows pending dot when there are pending proposals", async () => {
    const { usePathname } = vi.mocked(await import("next/navigation"));
    usePathname.mockReturnValue("/expansion");

    const { api } = await import("@/lib/api");
    vi.mocked(api.getProposals).mockResolvedValue([
      { id: "1", status: "pending" } as Parameters<typeof api.getProposals>[0] extends string
        ? never
        : never,
    ] as Awaited<ReturnType<typeof api.getProposals>>);

    render(<Nav />);
    await screen.findByLabelText("1 pending proposals");
  });
});
