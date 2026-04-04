import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Events } from "@/components/Events";

vi.mock("@/lib/api", () => ({
  api: {
    getEvents: vi.fn().mockResolvedValue({
      content: "# Economic Events\n\n**Monday**: Fed meeting minutes released.",
    }),
  },
}));

describe("Events", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Events />);
    expect(screen.getByText(/Loading events/)).toBeInTheDocument();
  });

  it("renders section title", async () => {
    render(<Events />);
    expect(await screen.findByText("Economic Events Calendar")).toBeInTheDocument();
  });

  it("renders events content", async () => {
    render(<Events />);
    expect(await screen.findByText(/Fed meeting minutes/)).toBeInTheDocument();
  });

  it("shows empty state when no content", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getEvents).mockResolvedValue({ content: "" });

    render(<Events />);
    expect(await screen.findByText(/No events calendar yet/)).toBeInTheDocument();
  });

  it("shows empty state for placeholder content", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getEvents).mockResolvedValue({
      content: "No events calendar generated yet.",
    });

    render(<Events />);
    expect(await screen.findByText(/No events calendar yet/)).toBeInTheDocument();
  });
});
