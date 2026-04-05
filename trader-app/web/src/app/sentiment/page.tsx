import { PageDescription } from "@/components/PageDescription";
import { Sentiment } from "@/components/Sentiment";

export default function SentimentPage() {
  return (
    <>
      <PageDescription title="What is Market Sentiment?">
        Sentiment analysis reads news headlines and market commentary to gauge whether
        the overall mood is optimistic (bullish) or pessimistic (bearish). Markets are
        driven by human emotions as much as by data — fear can cause sell-offs and
        excitement can drive rallies. The sentiment agent classifies recent headlines
        and gives the trading agent a qualitative signal to complement the quantitative
        technical indicators.
      </PageDescription>
      <Sentiment />
    </>
  );
}
