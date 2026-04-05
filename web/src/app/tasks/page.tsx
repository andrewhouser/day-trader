import { PageDescription } from "@/components/PageDescription";
import { Tasks } from "@/components/Tasks";

export default function TasksPage() {
  return (
    <>
      <PageDescription title="Scheduled Tasks">
        The trading system runs on a schedule of automated tasks — from overnight market
        monitors that track Asia and Europe, to the core trading agent that analyzes and
        executes trades during U.S. market hours. This page shows every scheduled task,
        when it last ran, and lets you trigger any task manually or adjust its schedule.
      </PageDescription>
      <Tasks />
    </>
  );
}
