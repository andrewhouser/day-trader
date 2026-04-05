import { PageDescription } from "@/components/PageDescription";
import { Performance } from "@/components/Performance";

export default function PerformancePage() {
  return (
    <>
      <PageDescription title="Performance Analysis">
        This page shows how well the trading agent has performed over time. Key metrics
        include <em>win rate</em> (what percentage of trades made money), <em>profit factor</em> (how
        much was gained on winners vs. lost on losers), and <em>max drawdown</em> (the largest
        peak-to-trough decline). The score dimension weights show which factors have
        historically been most predictive for each instrument — the agent learns and
        adjusts these over time.
      </PageDescription>
      <Performance />
    </>
  );
}
