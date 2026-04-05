import { PageDescription } from "@/components/PageDescription";
import { Reflections } from "@/components/Reflections";

export default function ReflectionsPage() {
  return (
    <>
      <PageDescription title="Agent Reflections">
        After every trading cycle and every closed position, the agent writes a reflection
        on what happened and why. Did the original hypothesis hold up? Was the timing right?
        What should change next time? This learning loop is how the agent improves over time —
        it builds institutional memory from its own experience rather than repeating the same
        mistakes.
      </PageDescription>
      <Reflections />
    </>
  );
}
