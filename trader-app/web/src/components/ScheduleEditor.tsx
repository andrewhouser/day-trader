"use client";

import { useState } from "react";

interface ScheduleEditorProps {
  taskId: string;
  taskName: string;
  currentCron: string;
  onSave: (taskId: string, cron: string) => Promise<void>;
  onClose: () => void;
}

type FrequencyType = "every_n_min" | "times_per_day" | "daily" | "weekly";

interface ScheduleState {
  frequency: FrequencyType;
  intervalMin: number;
  hourStart: number;
  hourEnd: number;
  times: number[];
  dailyHour: number;
  dailyMin: number;
  days: number[];
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_VALUES = [1, 2, 3, 4, 5, 6, 0];

function fmtHour(h: number): string {
  if (h === 0) return "12 AM";
  if (h < 12) return `${h} AM`;
  if (h === 12) return "12 PM";
  return `${h - 12} PM`;
}

function parseCronToState(cron: string): ScheduleState {
  const defaults: ScheduleState = {
    frequency: "daily",
    intervalMin: 10,
    hourStart: 9,
    hourEnd: 16,
    times: [8],
    dailyHour: 7,
    dailyMin: 0,
    days: [1, 2, 3, 4, 5],
  };

  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return defaults;
  const [minute, hour, , , dow] = parts;

  // Parse days
  let days = [1, 2, 3, 4, 5];
  if (dow !== "*") {
    const range = dow.match(/^(\d)-(\d)$/);
    if (range) {
      const from = parseInt(range[1]);
      const to = parseInt(range[2]);
      days = [];
      for (let d = from; d <= to; d++) days.push(d);
    } else if (/^\d$/.test(dow)) {
      days = [parseInt(dow)];
    } else if (dow.includes(",")) {
      days = dow.split(",").map(Number);
    }
  }

  // Every N minutes: */3 or 5/10
  const everyN = minute.match(/^\*\/(\d+)$/) || minute.match(/^\d+\/(\d+)$/);
  if (everyN) {
    const hourRange = hour.match(/^(\d+)-(\d+)$/);
    return {
      ...defaults,
      frequency: "every_n_min",
      intervalMin: parseInt(everyN[1]),
      hourStart: hourRange ? parseInt(hourRange[1]) : 9,
      hourEnd: hourRange ? parseInt(hourRange[2]) : 16,
      days,
    };
  }

  // Comma minutes with hour range: 0,30 9-16
  if (minute.includes(",") && hour.includes("-")) {
    const mins = minute.split(",").map(Number);
    const interval = mins.length === 2 && mins[0] === 0 ? mins[1] : 30;
    const hourRange = hour.match(/^(\d+)-(\d+)$/);
    return {
      ...defaults,
      frequency: "every_n_min",
      intervalMin: interval,
      hourStart: hourRange ? parseInt(hourRange[1]) : 9,
      hourEnd: hourRange ? parseInt(hourRange[2]) : 16,
      days,
    };
  }

  // Multiple hours: 0 8,12,16
  if (/^\d+$/.test(minute) && hour.includes(",")) {
    return {
      ...defaults,
      frequency: "times_per_day",
      times: hour.split(",").map(Number),
      dailyMin: parseInt(minute),
      days,
    };
  }

  // Single time: 0 7
  if (/^\d+$/.test(minute) && /^\d+$/.test(hour)) {
    const h = parseInt(hour);
    const m = parseInt(minute);
    if (days.length === 1 || (dow !== "*" && !dow.includes("-") && !dow.includes(","))) {
      return { ...defaults, frequency: "weekly", dailyHour: h, dailyMin: m, days };
    }
    return { ...defaults, frequency: "daily", dailyHour: h, dailyMin: m, days };
  }

  return defaults;
}

function stateToCron(s: ScheduleState): string {
  const dayStr = s.days.length === 7 ? "*" : s.days.join(",");

  switch (s.frequency) {
    case "every_n_min":
      return `*/${s.intervalMin} ${s.hourStart}-${s.hourEnd} * * ${dayStr}`;
    case "times_per_day": {
      const sorted = [...s.times].sort((a, b) => a - b);
      return `${s.dailyMin} ${sorted.join(",")} * * ${dayStr}`;
    }
    case "daily":
    case "weekly":
      return `${s.dailyMin} ${s.dailyHour} * * ${dayStr}`;
  }
}

function describeSchedule(s: ScheduleState): string {
  const dayNames = s.days.map((d) => DAY_LABELS[DAY_VALUES.indexOf(d)] ?? d).join(", ");

  switch (s.frequency) {
    case "every_n_min":
      return `Every ${s.intervalMin} min, ${fmtHour(s.hourStart)}–${fmtHour(s.hourEnd)}, ${dayNames}`;
    case "times_per_day": {
      const sorted = [...s.times].sort((a, b) => a - b);
      const timeStr = sorted.map(fmtHour).join(", ");
      return `${timeStr}, ${dayNames}`;
    }
    case "daily":
    case "weekly": {
      const m = s.dailyMin > 0 ? `:${s.dailyMin.toString().padStart(2, "0")}` : "";
      return `${fmtHour(s.dailyHour)}${m}, ${dayNames}`;
    }
  }
}

export default function ScheduleEditor({ taskId, taskName, currentCron, onSave, onClose }: ScheduleEditorProps) {
  const [state, setState] = useState<ScheduleState>(() => parseCronToState(currentCron));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(patch: Partial<ScheduleState>) {
    setState((prev) => ({ ...prev, ...patch }));
  }

  function toggleDay(day: number) {
    setState((prev) => {
      const has = prev.days.includes(day);
      const next = has ? prev.days.filter((d) => d !== day) : [...prev.days, day].sort((a, b) => a - b);
      return { ...prev, days: next.length > 0 ? next : prev.days };
    });
  }

  function addTime() {
    setState((prev) => {
      const next = [...prev.times];
      const last = next[next.length - 1] ?? 8;
      if (last + 2 <= 23) next.push(last + 2);
      return { ...prev, times: next };
    });
  }

  function removeTime(idx: number) {
    setState((prev) => {
      if (prev.times.length <= 1) return prev;
      return { ...prev, times: prev.times.filter((_, i) => i !== idx) };
    });
  }

  function setTime(idx: number, val: number) {
    setState((prev) => {
      const next = [...prev.times];
      next[idx] = val;
      return { ...prev, times: next };
    });
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await onSave(taskId, stateToCron(state));
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const preview = describeSchedule(state);
  const cronPreview = stateToCron(state);

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={`Edit schedule for ${taskName}`}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ fontWeight: 600, fontSize: "1.05rem" }}>Edit Schedule: {taskName}</div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "1.2rem", cursor: "pointer", padding: "0.25rem" }} aria-label="Close">✕</button>
        </div>

        {/* Frequency type */}
        <div className="sched-field">
          <label className="sched-label">Frequency</label>
          <select value={state.frequency} onChange={(e) => update({ frequency: e.target.value as FrequencyType })} className="sched-select">
            <option value="every_n_min">Every N minutes</option>
            <option value="times_per_day">Specific times per day</option>
            <option value="daily">Once daily</option>
            <option value="weekly">Once weekly</option>
          </select>
        </div>

        {/* Interval options */}
        {state.frequency === "every_n_min" && (
          <>
            <div className="sched-field">
              <label className="sched-label">Every</label>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <select value={state.intervalMin} onChange={(e) => update({ intervalMin: parseInt(e.target.value) })} className="sched-select" style={{ width: "auto" }}>
                  {[1, 2, 3, 5, 10, 15, 20, 30].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
                <span>minutes</span>
              </div>
            </div>
            <div className="sched-field">
              <label className="sched-label">Between</label>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <select value={state.hourStart} onChange={(e) => update({ hourStart: parseInt(e.target.value) })} className="sched-select" style={{ width: "auto" }}>
                  {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{fmtHour(i)}</option>)}
                </select>
                <span>and</span>
                <select value={state.hourEnd} onChange={(e) => update({ hourEnd: parseInt(e.target.value) })} className="sched-select" style={{ width: "auto" }}>
                  {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{fmtHour(i)}</option>)}
                </select>
              </div>
            </div>
          </>
        )}

        {/* Specific times */}
        {state.frequency === "times_per_day" && (
          <div className="sched-field">
            <label className="sched-label">Run at</label>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              {state.times.map((t, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <select value={t} onChange={(e) => setTime(i, parseInt(e.target.value))} className="sched-select" style={{ width: "auto" }}>
                    {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{fmtHour(h)}</option>)}
                  </select>
                  {state.times.length > 1 && (
                    <button onClick={() => removeTime(i)} style={{ background: "none", border: "none", color: "var(--red)", cursor: "pointer", fontSize: "0.9rem", padding: "0.2rem" }}>✕</button>
                  )}
                </div>
              ))}
              <button onClick={addTime} style={{ alignSelf: "flex-start", fontSize: "0.8rem", padding: "0.25rem 0.5rem" }}>+ Add time</button>
            </div>
          </div>
        )}

        {/* Daily / Weekly time */}
        {(state.frequency === "daily" || state.frequency === "weekly") && (
          <div className="sched-field">
            <label className="sched-label">Time</label>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <select value={state.dailyHour} onChange={(e) => update({ dailyHour: parseInt(e.target.value) })} className="sched-select" style={{ width: "auto" }}>
                {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{fmtHour(i)}</option>)}
              </select>
              <span>:</span>
              <select value={state.dailyMin} onChange={(e) => update({ dailyMin: parseInt(e.target.value) })} className="sched-select" style={{ width: "auto" }}>
                {[0, 5, 10, 15, 20, 30, 45].map((m) => <option key={m} value={m}>{m.toString().padStart(2, "0")}</option>)}
              </select>
            </div>
          </div>
        )}

        {/* Day picker */}
        <div className="sched-field">
          <label className="sched-label">Days</label>
          <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
            {DAY_LABELS.map((label, i) => {
              const val = DAY_VALUES[i];
              const active = state.days.includes(val);
              return (
                <button
                  key={val}
                  onClick={() => toggleDay(val)}
                  className={`badge ${active ? "badge-blue" : "badge-gray"}`}
                  style={{ cursor: "pointer", padding: "0.35rem 0.6rem", border: "none", fontSize: "0.8rem" }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Preview */}
        <div style={{ marginTop: "1rem", padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: 6, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.25rem" }}>Preview</div>
          <div style={{ fontSize: "0.9rem" }}>{preview}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.15rem", fontFamily: "monospace" }}>{cronPreview}</div>
        </div>

        {error && <div style={{ color: "var(--red)", fontSize: "0.85rem", marginTop: "0.5rem" }}>{error}</div>}

        {/* Actions */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Schedule"}
          </button>
        </div>
      </div>
    </div>
  );
}
