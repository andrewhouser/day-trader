import { Chat } from "@/components/Chat";
import { PageDescription } from "@/components/PageDescription";

export default function ChatPage() {
  return (
    <>
      <PageDescription title="Chat with the Agent">
        Ask the trading agent questions about its decisions, current positions, market
        outlook, or strategy. The agent has access to its full context — portfolio state,
        recent trades, research, risk alerts, and reflections — so it can explain its
        reasoning in detail.
      </PageDescription>
      <Chat />
    </>
  );
}
