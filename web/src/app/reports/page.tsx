import { PageDescription } from "@/components/PageDescription";
import { Reports } from "@/components/Reports";

export default function ReportsPage() {
  return (
    <>
      <PageDescription title="Daily Reports">
        Each morning, the agent produces a comprehensive report covering its portfolio
        status, overnight global market activity (Asia and Europe), recent trades and
        their outcomes, and its outlook for the day ahead. These reports are the agent&apos;s
        daily journal — a complete snapshot of its thinking at the start of each session.
      </PageDescription>
      <Reports />
    </>
  );
}
