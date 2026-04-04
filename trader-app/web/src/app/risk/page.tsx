import { RiskAlerts } from "@/components/RiskAlerts";
import { StressTest } from "@/components/StressTest";

import styles from "./page.module.css";

export default function RiskPage() {
  return (
    <div className={styles.container}>
      <RiskAlerts />
      <StressTest />
    </div>
  );
}
