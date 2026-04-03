"use client";

import { useEffect, useState, useCallback } from "react";
import { api, TaskInfo, TaskHistoryEntry } from "@/lib/api";
import { cronToHuman } from "@/lib/cron";
import ScheduleEditor from "./ScheduleEditor";

export default function Tasks() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [history, setHistory] = useState<TaskHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");
  const [editingTask, setEditingTask] = useState<TaskInfo | null>(null);

  const load = useCallback(async () => {
    try {
      const [t, h] = await Promise.all([api.getTasks(), api.getTaskHistory()]);
      setTasks(t);
      setHistory(h);
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

  async function handleScheduleSave(taskId: string, cron: string) {
    await api.updateTaskSchedule(taskId, cron);
    setActionMsg(`Schedule updated for ${taskId}`);
    await load();
  }

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading tasks...</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingBottom: "2rem" }}>
      {actionMsg && (
        <div className="card" style={{ padding: "0.75rem", fontSize: "0.85rem", color: "var(--blue)" }}>
          {actionMsg}
        </div>
      )}

      <div className="section-title">Agent Tasks</div>
      <div className="grid-2">
        {tasks.map((task) => (
          <div key={task.task_id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
              <div>
                <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{task.name}</div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{cronToHuman(task.cron)}</span>
                  <button
                    onClick={() => setEditingTask(task)}
                    style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "0.1rem 0.25rem", fontSize: "0.75rem", lineHeight: 1 }}
                    title="Edit schedule"
                    aria-label={`Edit schedule for ${task.name}`}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M8.5 1.5l2 2L3.5 10.5H1.5v-2z" />
                      <path d="M7 3l2 2" />
                    </svg>
                  </button>
                </div>
              </div>
              {task.is_running ? (
                <span className="badge badge-yellow">Running <span className="spinner" style={{ marginLeft: 4 }} /></span>
              ) : (
                <span className="badge badge-green">Idle</span>
              )}
            </div>

            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
              Last run: {task.last_run ? new Date(task.last_run.started_at).toLocaleString() : "Never"}
              {task.last_run?.finished_at && (
                <> · Finished: {new Date(task.last_run.finished_at).toLocaleString()}</>
              )}
              {task.last_run?.status && (
                <> · <span className={`badge ${task.last_run.status === "completed" ? "badge-green" : task.last_run.status === "failed" || task.last_run.status === "cancelled" ? "badge-red" : "badge-yellow"}`}>
                  {task.last_run.status}
                </span></>
              )}
              {task.last_run?.error && (
                <div style={{ color: "var(--red)", marginTop: "0.25rem" }}>Error: {task.last_run.error}</div>
              )}
            </div>

            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                className="primary"
                onClick={() => handleRun(task.task_id)}
                disabled={task.is_running}
              >
                ▶ Run Now
              </button>
              <button
                className="danger"
                onClick={() => handleStop(task.task_id)}
                disabled={!task.is_running}
              >
                ■ Stop
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Execution History */}
      <div className="section-title" style={{ marginTop: "0.5rem" }}>Execution History</div>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {history.length === 0 ? (
          <div className="empty-state" style={{ padding: "1.5rem" }}>No task executions yet</div>
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
                  <td style={{ fontWeight: 600 }}>{entry.task_name}</td>
                  <td>
                    <span className={`badge ${entry.status === "completed" ? "badge-green" : entry.status === "failed" || entry.status === "cancelled" ? "badge-red" : "badge-yellow"}`}>
                      {entry.status}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.8rem" }}>{new Date(entry.started_at).toLocaleString()}</td>
                  <td style={{ fontSize: "0.8rem" }}>{entry.finished_at ? new Date(entry.finished_at).toLocaleString() : "—"}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--red)", maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {entry.error || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
        Auto-refreshes every 5s
      </div>

      {/* Schedule Editor Modal */}
      {editingTask && (
        <ScheduleEditor
          taskId={editingTask.task_id}
          taskName={editingTask.name}
          currentCron={editingTask.cron}
          onSave={handleScheduleSave}
          onClose={() => setEditingTask(null)}
        />
      )}
    </div>
  );
}
