"use client";

import { useState } from "react";

import styles from "./ScheduleEditor.module.css";

interface Props {
  currentCron: string;
  onClose: () => void;
  onSave: (taskId: string, cron: string) => Promise<void>;
  taskId: string;
  taskName: string;
}

type FrequencyType = "daily" | "every_n_min" | "times_per_day" | "weekly";

interface ScheduleState {
  dailyHour: number;
  dailyMin: number;
  days: number[];
  frequency: FrequencyType;
  hourEnd: number;
  hourStart: number;
  intervalMin: number;
  times: number[];
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_VALUES = [1, 2, 3, 4, 5, 6, 0];

function describeSchedule(s: ScheduleState): string {
  const dayNames = s.days.map((d) => DAY_LABELS[DAY_VALUES.indexOf(d)] ?? d).join(", ");
  switch (s.frequency) {
    case "every_n_min":
      return `Every ${s.intervalMin} min, ${fmtHour(s.hourStart)}–${fmtHour(s.hourEnd)}, ${dayNames}`;
    case "times_per_day": {
      const timeStr = [...s.times].sort((a, b) => a - b).map(fmtHour).join(", ");
      return `${timeStr}, ${dayNames}`;
    }
    case "daily":
    case "weekly": {
      const m = s.dailyMin > 0 ? `:${s.dailyMin.toString().padStart(2, "0")}` : "";
      return `${fmtHour(s.dailyHour)}${m}, ${dayNames}`;
    }
  }
}

function fmtHour(h: number): string {
  if (h === 0) return "12 AM";
  if (h < 12) return `${h} AM`;
  if (h === 12) return "12 PM";
  return `${h - 12} PM`;
}

function parseCronToState(cron: string): ScheduleState {
  const defaults: ScheduleState = {
    dailyHour: 7,
    dailyMin: 0,
    days: [1, 2, 3, 4, 5],
    frequency: "daily",
    hourEnd: 16,
    hourStart: 9,
    intervalMin: 10,
    times: [8],
  };

  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return defaults;
  const [minute, hour, , , dow] = parts;

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

  const everyN = minute.match(/^\*\/(\d+)$/) || minute.match(/^\d+\/(\d+)$/);
  if (everyN) {
    const hourRange = hour.match(/^(\d+)-(\d+)$/);
    return {
      ...defaults,
      days,
      frequency: "every_n_min",
      hourEnd: hourRange ? parseInt(hourRange[2]) : 16,
      hourStart: hourRange ? parseInt(hourRange[1]) : 9,
      intervalMin: parseInt(everyN[1]),
    };
  }

  if (minute.includes(",") && hour.includes("-")) {
    const mins = minute.split(",").map(Number);
    const interval = mins.length === 2 && mins[0] === 0 ? mins[1] : 30;
    const hourRange = hour.match(/^(\d+)-(\d+)$/);
    return {
      ...defaults,
      days,
      frequency: "every_n_min",
      hourEnd: hourRange ? parseInt(hourRange[2]) : 16,
      hourStart: hourRange ? parseInt(hourRange[1]) : 9,
      intervalMin: interval,
    };
  }

  if (/^\d+$/.test(minute) && hour.includes(",")) {
    return {
      ...defaults,
      dailyMin: parseInt(minute),
      days,
      frequency: "times_per_day",
      times: hour.split(",").map(Number),
    };
  }

  if (/^\d+$/.test(minute) && /^\d+$/.test(hour)) {
    const h = parseInt(hour);
    const m = parseInt(minute);
    if (days.length === 1 || (dow !== "*" && !dow.includes("-") && !dow.includes(","))) {
      return { ...defaults, dailyHour: h, dailyMin: m, days, frequency: "weekly" };
    }
    return { ...defaults, dailyHour: h, dailyMin: m, days, frequency: "daily" };
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

export function ScheduleEditor({ currentCron, onClose, onSave, taskId, taskName }: Props) {
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [state, setState] = useState<ScheduleState>(() => parseCronToState(currentCron));

  function addTime() {
    setState((prev) => {
      const next = [...prev.times];
      const last = next[next.length - 1] ?? 8;
      if (last + 2 <= 23) next.push(last + 2);
      return { ...prev, times: next };
    });
  }

  async function handleSave() {
    setError("");
    setSaving(true);
    try {
      await onSave(taskId, stateToCron(state));
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
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

  function toggleDay(day: number) {
    setState((prev) => {
      const has = prev.days.includes(day);
      const next = has
        ? prev.days.filter((d) => d !== day)
        : [...prev.days, day].sort((a, b) => a - b);
      return { ...prev, days: next.length > 0 ? next : prev.days };
    });
  }

  function update(patch: Partial<ScheduleState>) {
    setState((prev) => ({ ...prev, ...patch }));
  }

  const cronPreview = stateToCron(state);
  const preview = describeSchedule(state);

  return (
    <div
      aria-label={`Edit schedule for ${taskName}`}
      aria-modal="true"
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
    >
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.headerTitle}>Edit Schedule: {taskName}</div>
          <button aria-label="Close" className={styles.closeButton} onClick={onClose}>
            ✕
          </button>
        </div>

        <div className={styles.schedField}>
          <label className={styles.schedLabel}>Frequency</label>
          <select
            className={styles.schedSelect}
            onChange={(e) => update({ frequency: e.target.value as FrequencyType })}
            value={state.frequency}
          >
            <option value="daily">Once daily</option>
            <option value="every_n_min">Every N minutes</option>
            <option value="times_per_day">Specific times per day</option>
            <option value="weekly">Once weekly</option>
          </select>
        </div>

        {state.frequency === "every_n_min" && (
          <>
            <div className={styles.schedField}>
              <label className={styles.schedLabel}>Every</label>
              <div className={styles.inlineRow}>
                <select
                  className={styles.schedSelectAuto}
                  onChange={(e) => update({ intervalMin: parseInt(e.target.value) })}
                  value={state.intervalMin}
                >
                  {[1, 2, 3, 5, 10, 15, 20, 30].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
                <span>minutes</span>
              </div>
            </div>
            <div className={styles.schedField}>
              <label className={styles.schedLabel}>Between</label>
              <div className={styles.inlineRow}>
                <select
                  className={styles.schedSelectAuto}
                  onChange={(e) => update({ hourStart: parseInt(e.target.value) })}
                  value={state.hourStart}
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {fmtHour(i)}
                    </option>
                  ))}
                </select>
                <span>and</span>
                <select
                  className={styles.schedSelectAuto}
                  onChange={(e) => update({ hourEnd: parseInt(e.target.value) })}
                  value={state.hourEnd}
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>
                      {fmtHour(i)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </>
        )}

        {state.frequency === "times_per_day" && (
          <div className={styles.schedField}>
            <label className={styles.schedLabel}>Run at</label>
            <div className={styles.timesColumn}>
              {state.times.map((t, i) => (
                <div className={styles.timesRow} key={i}>
                  <select
                    className={styles.schedSelectAuto}
                    onChange={(e) => setTime(i, parseInt(e.target.value))}
                    value={t}
                  >
                    {Array.from({ length: 24 }, (_, h) => (
                      <option key={h} value={h}>
                        {fmtHour(h)}
                      </option>
                    ))}
                  </select>
                  {state.times.length > 1 && (
                    <button
                      className={styles.removeTimeButton}
                      onClick={() => removeTime(i)}
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addTime}
                style={{ alignSelf: "flex-start", fontSize: "0.8rem", padding: "0.25rem 0.5rem" }}
              >
                + Add time
              </button>
            </div>
          </div>
        )}

        {(state.frequency === "daily" || state.frequency === "weekly") && (
          <div className={styles.schedField}>
            <label className={styles.schedLabel}>Time</label>
            <div className={styles.inlineRow}>
              <select
                className={styles.schedSelectAuto}
                onChange={(e) => update({ dailyHour: parseInt(e.target.value) })}
                value={state.dailyHour}
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>
                    {fmtHour(i)}
                  </option>
                ))}
              </select>
              <span>:</span>
              <select
                className={styles.schedSelectAuto}
                onChange={(e) => update({ dailyMin: parseInt(e.target.value) })}
                value={state.dailyMin}
              >
                {[0, 5, 10, 15, 20, 30, 45].map((m) => (
                  <option key={m} value={m}>
                    {m.toString().padStart(2, "0")}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <div className={styles.schedField}>
          <label className={styles.schedLabel}>Days</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
            {DAY_LABELS.map((label, i) => {
              const val = DAY_VALUES[i];
              const active = state.days.includes(val);
              return (
                <button
                  className={`badge ${active ? "badge-blue" : "badge-gray"}`}
                  key={val}
                  onClick={() => toggleDay(val)}
                  style={{ border: "none", cursor: "pointer", fontSize: "0.8rem", padding: "0.35rem 0.6rem" }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        <div className={styles.preview}>
          <div className={styles.previewLabel}>Preview</div>
          <div className={styles.previewText}>{preview}</div>
          <div className={styles.previewCron}>{cronPreview}</div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.footer}>
          <button onClick={onClose}>Cancel</button>
          <button className="primary" disabled={saving} onClick={handleSave}>
            {saving ? "Saving..." : "Save Schedule"}
          </button>
        </div>
      </div>
    </div>
  );
}
