"use client";

import { useEffect, useState } from "react";

import { api, StressTestResult } from "@/lib/api";

import { ScenarioCard } from "./ScenarioCard";
import styles from "./StressTest.module.css";

export function StressTest() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<StressTestResult | null>(null);

  function load() {
    setError("");
    setLoading(true);
    api
      .getStressTest()
      .then(setResult)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Running stress scenarios...
      </div>
    );
  }
  if (error) {
    return <div className="card" style={{ color: "var(--red)" }}>Error: {error}</div>;
  }
  if (!result) return null;

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div className={`section-title ${styles.sectionTitleInline}`}>
          Portfolio Stress Scenarios
        </div>
        <button className={styles.rerunButton} onClick={load}>
          Re-run
        </button>
      </div>
      {result.scenarios.map((s, i) => (
        <ScenarioCard currentValue={result.current_portfolio_value} key={i} scenario={s} />
      ))}
      <div className={styles.timestamp}>
        Cached for 5 minutes · Last run: {new Date(result.timestamp).toLocaleString()}
      </div>
    </div>
  );
}
