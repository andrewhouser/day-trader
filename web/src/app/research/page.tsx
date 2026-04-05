import { PageDescription } from "@/components/PageDescription";
import { Research } from "@/components/Research";

export default function ResearchPage() {
  return (
    <>
      <PageDescription title="Market Research">
        The research agent gathers data from multiple sources — economic databases, financial
        news, SEC filings, and market data providers — then synthesizes it into a structured
        analysis. It identifies the dominant market narratives, assesses risk factors, and
        highlights instruments worth watching. This is the agent&apos;s homework before it makes
        any trading decisions.
      </PageDescription>
      <Research />
    </>
  );
}
