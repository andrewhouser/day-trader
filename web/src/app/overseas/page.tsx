import { Overseas } from "@/components/Overseas";
import { PageDescription } from "@/components/PageDescription";

export default function OverseasPage() {
  return (
    <>
      <PageDescription title="Overseas Markets">
        The overnight monitors track global markets while the U.S. is closed. The Nikkei
        monitor watches the Tokyo Stock Exchange (7–10:30 PM ET), the FTSE monitor tracks
        London (2:30–5:30 AM ET), and the handoff summary synthesizes everything into a
        single pre-market briefing at 5:30 AM ET. When significant moves are detected in
        international ETFs, trade signals are emitted for the U.S. trading agent to evaluate.
      </PageDescription>
      <Overseas />
    </>
  );
}
