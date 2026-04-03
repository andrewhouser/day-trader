import RiskAlerts from "@/components/RiskAlerts";
import StressTest from "@/components/StressTest";

export default function RiskPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", paddingBottom: "2rem" }}>
      <RiskAlerts />
      <StressTest />
    </div>
  );
}
