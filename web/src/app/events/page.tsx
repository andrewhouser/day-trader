import { Events } from "@/components/Events";
import { PageDescription } from "@/components/PageDescription";

export default function EventsPage() {
  return (
    <>
      <PageDescription title="Economic Events Calendar">
        Scheduled economic events — like Federal Reserve meetings, jobs reports, and
        inflation data releases — can cause sudden market moves. The events agent tracks
        these upcoming catalysts so the trading agent can avoid opening risky positions
        right before a high-impact announcement, or prepare to act on the outcome.
      </PageDescription>
      <Events />
    </>
  );
}
