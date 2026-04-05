import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Reports } from "@/components/Reports";

const mockReports = [
  { date: "2026-01-03", filename: "report_2026-01-03.md" },
  { date: "2026-01-02", filename: "report_2026-01-02.md" },
];

vi.mock("@/lib/api", () => ({
  api: {
    getReport: vi.fn().mockResolvedValue({ content: "# Morning Report\n\nPortfolio up 2%.", filename: "report_2026-01-03.md" }),
    getReports: vi.fn().mockResolvedValue(mockReports),
  },
}));

describe("Reports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<Reports />);
    expect(screen.getByText(/Loading reports/)).toBeInTheDocument();
  });

  it("renders report count", async () => {
    render(<Reports />);
    expect(await screen.findByText("Morning Reports (2)")).toBeInTheDocument();
  });

  it("renders report dates", async () => {
    render(<Reports />);
    await screen.findByText("2026-01-03");
    expect(screen.getByText("2026-01-02")).toBeInTheDocument();
  });

  it("marks first report as Latest", async () => {
    render(<Reports />);
    await screen.findByText("Latest");
  });

  it("loads and shows report content when accordion is clicked", async () => {
    const user = userEvent.setup();
    render(<Reports />);

    await screen.findByText("2026-01-03");
    await user.click(screen.getAllByRole("button")[0]);

    expect(await screen.findByText(/Portfolio up 2%/)).toBeInTheDocument();
  });

  it("shows empty state when no reports", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getReports).mockResolvedValue([]);

    render(<Reports />);
    expect(await screen.findByText("No morning reports generated yet.")).toBeInTheDocument();
  });
});
