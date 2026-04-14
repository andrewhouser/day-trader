"use client";

import { useCallback, useEffect, useState } from "react";

import { api, SettingEntry } from "@/lib/api";

import styles from "./Settings.module.css";

export function Settings() {
  const [groups, setGroups] = useState<Record<string, SettingEntry[]>>({});
  const [dirty, setDirty] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api.getSettings();
      setGroups(res.groups);
    } catch {
      setMessage("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleChange(key: string, raw: string, entry: SettingEntry) {
    const val = entry.type === "int" ? parseInt(raw, 10) : parseFloat(raw);
    if (isNaN(val)) return;
    setDirty((prev) => ({ ...prev, [key]: val }));
  }

  function handleReset(key: string) {
    setDirty((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  async function handleSave() {
    if (Object.keys(dirty).length === 0) return;
    setSaving(true);
    setMessage("");
    try {
      const res = await api.updateSettings(dirty);
      const count = Object.keys(res.applied).length;
      const errCount = res.errors?.length ?? 0;
      setMessage(
        `${count} setting${count !== 1 ? "s" : ""} saved` +
        (errCount > 0 ? ` · ${errCount} error${errCount !== 1 ? "s" : ""}: ${res.errors!.join(", ")}` : "")
      );
      setDirty({});
      await load();
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading settings...
      </div>
    );
  }

  const hasDirty = Object.keys(dirty).length > 0;
  const groupOrder = ["Risk Management", "Trading Aggressiveness", "Overseas Signals", "Rebalancer"];

  return (
    <div className={styles.container}>
      {message && (
        <div className={`card ${message.includes("error") || message.includes("Failed") ? styles.msgError : styles.msgSuccess}`}>
          {message}
        </div>
      )}

      {groupOrder.map((groupName) => {
        const entries = groups[groupName];
        if (!entries) return null;
        return (
          <div key={groupName}>
            <div className="section-title">{groupName}</div>
            <div className={styles.grid}>
              {entries.map((entry) => {
                const current = dirty[entry.key] ?? entry.value;
                const isDirty = entry.key in dirty;
                const step = entry.type === "int" ? 1 : 0.1;
                const displayValue = entry.type === "int"
                  ? current
                  : current.toFixed(entry.key === "speculation_max_position_pct" ? 2 : 1);
                return (
                  <div className={`card ${styles.settingCard}`} key={entry.key}>
                    <div className={styles.settingHeader}>
                      <span className={styles.settingLabel}>{entry.description}</span>
                      {isDirty && (
                        <button
                          className={styles.resetButton}
                          onClick={() => handleReset(entry.key)}
                          title="Reset to current value"
                        >
                          ↩
                        </button>
                      )}
                    </div>
                    <div className={styles.settingControl}>
                      <input
                        className={styles.slider}
                        max={entry.max}
                        min={entry.min}
                        onChange={(e) => handleChange(entry.key, e.target.value, entry)}
                        step={step}
                        type="range"
                        value={current}
                      />
                      <span className={`${styles.settingValue} ${isDirty ? styles.settingValueDirty : ""}`}>
                        {displayValue}
                      </span>
                    </div>
                    <div className={styles.settingRange}>
                      {entry.min} — {entry.max}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      <div className={styles.saveBar}>
        <button
          className="primary"
          disabled={!hasDirty || saving}
          onClick={handleSave}
        >
          {saving ? "Saving..." : `Save ${Object.keys(dirty).length} change${Object.keys(dirty).length !== 1 ? "s" : ""}`}
        </button>
        {hasDirty && (
          <span className={styles.dirtyHint}>
            {Object.keys(dirty).length} unsaved change{Object.keys(dirty).length !== 1 ? "s" : ""}
          </span>
        )}
      </div>
    </div>
  );
}
