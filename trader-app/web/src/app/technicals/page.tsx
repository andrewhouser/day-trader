import { PageDescription } from "@/components/PageDescription";
import { Technicals } from "@/components/Technicals";

export default function TechnicalsPage() {
  return (
    <>
      <PageDescription title="What are Technical Indicators?">
        Technical indicators are math-based signals derived from price and volume data.
        They help identify trends, momentum, and potential turning points without relying
        on opinions. For example, a <em>moving average</em> smooths out daily price noise
        to show the overall direction, while <em>RSI</em> (Relative Strength Index) measures
        whether something has been bought or sold too aggressively. The trading agent uses
        these indicators to score each instrument before deciding whether to buy, sell, or hold.
      </PageDescription>
      <Technicals />
    </>
  );
}
