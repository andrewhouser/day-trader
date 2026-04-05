import { Expansion } from "@/components/Expansion";
import { PageDescription } from "@/components/PageDescription";

export default function ExpansionPage() {
  return (
    <>
      <PageDescription title="Portfolio Expansion Proposals">
        The expansion agent periodically analyzes the portfolio for gaps in diversification
        and suggests new instruments (stocks, ETFs, REITs) that could improve risk-adjusted
        returns. Proposals require your explicit approval before the trading agent can trade
        them — this is your control point for deciding what the agent is allowed to invest in.
      </PageDescription>
      <Expansion />
    </>
  );
}
