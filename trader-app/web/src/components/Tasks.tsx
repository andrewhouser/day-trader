"use client";

import { useEffect, useState, useCallback } from "react";
import { api, TaskInfo, TaskHistoryEntry } from "@/lib/api";

export default function Tasks() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [history, setHistory] = useState<TaskHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

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

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading tasks...</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingBottom: "2rem" }}>
      {actionMsg && (
        <div className="card" style={{ padding: "0.75rem", fontSize: "0.85rem", color: "var(--blue)" }}>
          {actionMsg}
        </div>
      )}

      {/* Task Controls */}
      <div className="section-title">Agent Tasks</div>
      <div className="grid-2">
        {tasks.map((task) => (
          <div key={task.task_id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
              <div>
                <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{task.name}</div>
                <code style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{task.cron}</code>
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
                <> · <span className={`badge ${task.last_run.status === "completed" ? "badge-green" : task.last_run.status === "failed" ? "badge-red" : "badge-yellow"}`}>
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
                    <span className={`badge ${entry.status === "completed" ? "badge-green" : entry.status === "failed" ? "badge-red" : "badge-yellow"}`}>
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
    </div>
  );
}
