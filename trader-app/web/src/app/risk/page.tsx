import { PageDescription } from "@/components/PageDescription";
import { RiskAlerts } from "@/components/RiskAlerts";
import { StressTest } from "@/components/StressTest";

import styles from "./page.module.css";

export default function RiskPage() {
  return (
    <div className={styles.container}>
      <PageDescription title="Risk Management &amp; Stress Testing">
        Risk management is about protecting your portfolio from large losses. The risk
        monitor watches for sudden price swings, positions that have dropped past their
        stop-loss levels, and concentration risk (too much money in correlated assets).
        The stress test simulates &quot;what if&quot; scenarios — like a 5% market crash or a
        volatility spike — to show how the current portfolio would be affected before
        it actually happens. Think of it as a fire drill for your investments.
      </PageDescription>
      <RiskAlerts />
      <StressTest />
    </div>
  );
}
