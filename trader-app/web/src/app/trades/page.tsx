import { PageDescription } from "@/components/PageDescription";
import { Trades } from "@/components/Trades";

export default function TradesPage() {
  return (
    <>
      <PageDescription title="Trade Log">
        Every buy and sell decision the agent makes is recorded here with full reasoning.
        Each trade includes the instrument, price, quantity, and — most importantly — the
        agent&apos;s hypothesis for why it made the trade and what would prove it wrong. This
        transparency lets you see exactly how the agent thinks and whether its logic holds
        up over time.
      </PageDescription>
      <Trades />
    </>
  );
}
