"use client";

import { useCallback, useEffect, useState } from "react";

import { api, TaskHistoryEntry, TaskInfo } from "@/lib/api";
import { groupTasksByCategory } from "@/lib/constants";
import { cronToHuman } from "@/lib/cron";

import { ScheduleEditor } from "./ScheduleEditor";

import styles from "./Tasks.module.css";

const TASK_DESCRIPTIONS: Record<string, string> = {
  nikkei_open: "Tracks the Tokyo Stock Exchange morning session. Monitors Nikkei 225 levels, yen dynamics, and BOJ signals. Emits trade signals for EWJ on significant moves.",
  nikkei_reopen: "Tracks the Tokyo afternoon session after the midday break. Compares to the morning, captures momentum shifts, and prepares the Asia summary for Europe.",
  ftse_open: "Tracks the London Stock Exchange open. Monitors FTSE 100, European sector rotation, GBP/EUR dynamics, and BOE/ECB signals. Emits trade signals for EWU/EWG.",
  europe_handoff: "Synthesizes all overnight Asia and Europe data into a single pre-market briefing for the U.S. trading agent. Includes pending overseas trade signals.",
  compaction: "Summarizes old research, trade logs, and reflections into compressed history files to prevent unbounded file growth and keep the agent's context focused.",
  events: "Fetches upcoming economic events — Fed meetings, jobs reports, CPI, earnings — so the trading agent can avoid risky positions ahead of high-impact announcements.",
  morning_report: "Generates the daily summary: portfolio status, overnight global recap from Asia and Europe, recent trades, performance reflection, and market outlook.",
  research: "Gathers data from 7 sources (FRED, Finnhub, SEC EDGAR, and more), produces structured research notes, and triggers the trader if stop-loss or opportunity alerts fire.",
  hourly_check: "The core trading cycle. Reads all available intelligence, scores each instrument on 6 dimensions, runs bear-case debate on large trades, and executes buy/sell decisions.",
  sentiment: "Reads news headlines and classifies the overall market mood for each instrument as bullish, neutral, or bearish. Provides a qualitative signal for the trader.",
  risk_monitor: "Watches positions every 3 minutes for trailing stop breaches, take-profit targets, portfolio drawdown, volatility spikes, and correlation concentration risk.",
  rebalancer: "Weekly check on whether the portfolio has drifted from its target allocation. Suggests and executes trades to restore balance between asset classes.",
  performance: "Weekly deep-dive into trade outcomes: win rate, profit factor, per-instrument breakdown, holding periods, and pattern detection. Updates adaptive score weights.",
  expansion: "Evaluates potential new instruments for portfolio diversification. Generates proposals that require your approval before the trading agent can trade them.",
  playbook: "Reads all trade history and reflections, extracts recurring strategy patterns with empirical win rates. Suspends strategies that consistently underperform.",
  market_context: "Computes a rolling 30-day view of portfolio arc, regime transitions, trade statistics, best/worst instruments, and correlation structure.",
};

export function Tasks() {
  const [actionMsg, setActionMsg] = useState("");
  const [editingTask, setEditingTask] = useState<TaskInfo | null>(null);
  const [history, setHistory] = useState<TaskHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<TaskInfo[]>([]);

  const load = useCallback(async () => {
    try {
      const [t, h] = await Promise.all([api.getTasks(), api.getTaskHistory()]);
      setHistory(h);
      setTasks(t);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    load().finally(() => setLoading(false));
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  async function handleRun(taskId: string) {
    try {
      setActionMsg("");
      await api.runTask(taskId);
      setActionMsg(`Started ${taskId}`);
      setTimeout(load, 1000);
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Failed to start task");
    }
  }

  async function handleScheduleSave(taskId: string, cron: string) {
    await api.updateTaskSchedule(taskId, cron);
    setActionMsg(`Schedule updated for ${taskId}`);
    await load();
  }

  async function handleStop(taskId: string) {
    try {
      setActionMsg("");
      await api.stopTask(taskId);
      setActionMsg(`Stop requested for ${taskId}`);
      setTimeout(load, 1000);
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Failed to stop task");
    }
  }

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading tasks...
      </div>
    );
  }

  const grouped = groupTasksByCategory(tasks);

  return (
    <div className={styles.container}>
      {actionMsg && (
        <div className={`card ${styles.actionMsg}`}>{actionMsg}</div>
      )}

      <div className="section-title">Agent Tasks</div>
      {Object.entries(grouped).map(([category, categoryTasks]) => (
        <div key={category}>
          <div className={styles.categoryHeader}>{category}</div>
          <div className="grid-2">
            {categoryTasks.map((task) => (
          <div className="card" key={task.task_id}>
            <div className={styles.taskCardHeader}>
              <div>
                <div className={styles.taskName}>{task.name}</div>
                {TASK_DESCRIPTIONS[task.task_id] && (
                  <div className={styles.taskDesc}>{TASK_DESCRIPTIONS[task.task_id]}</div>
                )}
                <div className={styles.taskScheduleRow}>
                  <span className={styles.taskScheduleText}>{cronToHuman(task.cron)}</span>
                  <button
                    aria-label={`Edit schedule for ${task.name}`}
                    className={styles.editButton}
                    onClick={() => setEditingTask(task)}
                    title="Edit schedule"
                  >
                    <svg
                      fill="none"
                      height="12"
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="1.3"
                      viewBox="0 0 12 12"
                      width="12"
                    >
                      <path d="M8.5 1.5l2 2L3.5 10.5H1.5v-2z" />
                      <path d="M7 3l2 2" />
                    </svg>
                  </button>
                </div>
              </div>
              {task.is_running ? (
                <span className="badge badge-yellow">
                  Running <span className="spinner" style={{ marginLeft: 4 }} />
                </span>
              ) : (
                <span className="badge badge-green">Idle</span>
              )}
            </div>

            <div className={styles.taskMeta}>
              {task.next_run && (
                <div>Next run: {new Date(task.next_run).toLocaleString()}</div>
              )}
              Last run: {task.last_run ? new Date(task.last_run.started_at).toLocaleString() : "Never"}
              {task.last_run?.finished_at && (
                <> · Finished: {new Date(task.last_run.finished_at).toLocaleString()}</>
              )}
              {task.last_run?.status && (
                <>
                  {" "}
                  ·{" "}
                  <span
                    className={`badge ${task.last_run.status === "completed" ? "badge-green" : task.last_run.status === "failed" || task.last_run.status === "cancelled" ? "badge-red" : "badge-yellow"}`}
                  >
                    {task.last_run.status}
                  </span>
                </>
              )}
              {task.last_run?.error && (
                <div className={styles.errorText}>Error: {task.last_run.error}</div>
              )}
            </div>

            <div className={styles.taskActions}>
              <button
                className="primary"
                disabled={task.is_running}
                onClick={() => handleRun(task.task_id)}
              >
                ▶ Run Now
              </button>
              <button
                className="danger"
                disabled={!task.is_running}
                onClick={() => handleStop(task.task_id)}
              >
                ■ Stop
              </button>
            </div>
          </div>
        ))}
      </div>
      </div>
      ))}

      <div className="section-title" style={{ marginTop: "0.5rem" }}>Execution History</div>
      <div className={`card ${styles.historyCard}`}>
        {history.length === 0 ? (
          <div className="empty-state" style={{ padding: "1.5rem" }}>
            No task executions yet
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Status</th>
                <th>Started</th>
                <th>Finished</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry, i) => (
                <tr key={i}>
                  <td className={styles.historyNameCell}>{entry.task_name}</td>
                  <td>
                    <span
                      className={`badge ${entry.status === "completed" ? "badge-green" : entry.status === "failed" || entry.status === "cancelled" ? "badge-red" : "badge-yellow"}`}
                    >
                      {entry.status}
                    </span>
                  </td>
                  <td className={styles.historyDateCell}>
                    {new Date(entry.started_at).toLocaleString()}
                  </td>
                  <td className={styles.historyDateCell}>
                    {entry.finished_at ? new Date(entry.finished_at).toLocaleString() : "—"}
                  </td>
                  <td className={styles.historyErrorCell}>{entry.error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className={styles.timestamp}>Auto-refreshes every 5s</div>

      {editingTask && (
        <ScheduleEditor
          currentCron={editingTask.cron}
          onClose={() => setEditingTask(null)}
          onSave={handleScheduleSave}
          taskId={editingTask.task_id}
          taskName={editingTask.name}
        />
      )}
    </div>
  );
}
