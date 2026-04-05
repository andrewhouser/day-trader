import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Chat } from "@/components/Chat";

vi.mock("@/lib/api", () => ({
  api: {
    chat: vi.fn().mockResolvedValue({ response: "Hello! I'm the agent." }),
  },
}));

describe("Chat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the welcome state with placeholder text", () => {
    render(<Chat />);
    expect(
      screen.getByText(/Ask the agent about its trading decisions/)
    ).toBeInTheDocument();
  });

  it("renders the textarea and send button", () => {
    render(<Chat />);
    expect(screen.getByLabelText("Chat message input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("disables send button when input is empty", () => {
    render(<Chat />);
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("enables send button when user types", async () => {
    const user = userEvent.setup();
    render(<Chat />);

    await user.type(screen.getByLabelText("Chat message input"), "Hello");
    expect(screen.getByRole("button", { name: "Send" })).not.toBeDisabled();
  });

  it("sends message and displays response", async () => {
    const user = userEvent.setup();
    render(<Chat />);

    await user.type(screen.getByLabelText("Chat message input"), "Hello");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(await screen.findByText("Hello! I'm the agent.")).toBeInTheDocument();
  });

  it("clears input after sending", async () => {
    const user = userEvent.setup();
    render(<Chat />);

    const input = screen.getByLabelText("Chat message input") as HTMLTextAreaElement;
    await user.type(input, "Hello");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText("Hello! I'm the agent.");
    expect(input.value).toBe("");
  });

  it("shows error message when API fails", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.chat).mockRejectedValue(new Error("API error"));

    const user = userEvent.setup();
    render(<Chat />);

    await user.type(screen.getByLabelText("Chat message input"), "Hello");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText(/Error: API error/)).toBeInTheDocument();
  });

  it("sends on Enter key press", async () => {
    const user = userEvent.setup();
    render(<Chat />);

    await user.type(screen.getByLabelText("Chat message input"), "Hello{Enter}");
    expect(await screen.findByText("Hello! I'm the agent.")).toBeInTheDocument();
  });
});
