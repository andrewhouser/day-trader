import { News } from "@/components/News";
import { PageDescription } from "@/components/PageDescription";

export default function NewsPage() {
  return (
    <>
      <PageDescription title="Market News">
        Live headlines from financial news sources for the instruments the agent tracks.
        News drives short-term market moves — earnings surprises, policy changes, and
        geopolitical events can all shift prices quickly. The agent uses these headlines
        as one input into its sentiment analysis.
      </PageDescription>
      <News />
    </>
  );
}
