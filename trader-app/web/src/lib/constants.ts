import { TaskInfo } from "./api";

export const TASK_CATEGORY_ORDER = [
  "Overseas Monitors",
  "Core Trading",
  "Intelligence",
  "Risk & Portfolio",
  "Maintenance",
] as const;

export type TaskCategory = (typeof TASK_CATEGORY_ORDER)[number];

export function groupTasksByCategory(
  tasks: TaskInfo[],
): Record<string, TaskInfo[]> {
  const grouped: Record<string, TaskInfo[]> = {};
  for (const cat of TASK_CATEGORY_ORDER) {
    const items = tasks.filter((t) => t.category === cat);
    if (items.length > 0) grouped[cat] = items;
  }
  const knownIds = new Set(
    Object.values(grouped)
      .flat()
      .map((t) => t.task_id),
  );
  const uncategorized = tasks.filter((t) => !knownIds.has(t.task_id));
  if (uncategorized.length > 0) grouped["Other"] = uncategorized;
  return grouped;
}
