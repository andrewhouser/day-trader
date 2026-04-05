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

  it("renders all navigation groups", () => {
    render(<Nav />);
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Trading")).toBeInTheDocument();
    expect(screen.getByText("Analysis")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText("System")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    render(<Nav />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
    expect(screen.getByText("Technicals")).toBeInTheDocument();
    expect(screen.getByText("Tasks")).toBeInTheDocument();
    expect(screen.getByText("Chat")).toBeInTheDocument();
  });

  it("marks the active link based on pathname", () => {
    const { usePathname } = vi.mocked(await import("next/navigation"));
    usePathname.mockReturnValue("/trades");

    render(<Nav />);
    const tradesLink = screen.getByRole("tab", { name: "Trades" });
    expect(tradesLink).toHaveAttribute("aria-selected", "true");
  });

  it("has main navigation role", () => {
    render(<Nav />);
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("shows pending dot when there are pending proposals", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getProposals).mockResolvedValue([
      { id: "1", status: "pending" } as Parameters<typeof api.getProposals>[0] extends string
        ? never
        : never,
    ] as Awaited<ReturnType<typeof api.getProposals>>);

    render(<Nav />);
    // pending dot aria-label should appear after async check
    await screen.findByLabelText("1 pending proposals");
  });
});
