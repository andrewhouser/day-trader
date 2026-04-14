import { PageDescription } from "@/components/PageDescription";
import { Settings } from "@/components/Settings";

export default function SettingsPage() {
  return (
    <>
      <PageDescription title="Agent Settings">
        Tune the trading agent&apos;s risk management and aggressiveness in real time.
        Changes take effect immediately on the next agent cycle and persist across
        restarts. Drag the sliders to adjust, then click Save.
      </PageDescription>
      <Settings />
    </>
  );
}
