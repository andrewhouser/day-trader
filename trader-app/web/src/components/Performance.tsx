"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { api, ScoreWeightsResult } from "@/lib/api";

import styles from "./Performance.module.css";

const DIMS = [
  "event_risk",
  "momentum",
  "risk_reward",
  "sector_divergence",
  "sentiment",
  "trend",
];

function weightColor(v: number): string {
  if (v > 1.0) return "var(--green)";
  if (v < 1.0) return "var(--red)";
  return "var(--text-muted)";
}

export function Performance() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [weights, setWeights] = useState<ScoreWeightsResult | null>(null);

  useEffect(() => {
    Promise.all([
      api.getPerformance(10).then(setEntries),
      api.getScoreWeights().then(setWeights).catch(() => null),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading performance...
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {weights && Object.keys(weights.weights).length > 0 && (
        <>
          <div className="section-title">Score Dimension Weights</div>
          <div className={`card ${styles.overflowX}`}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  {DIMS.map((d) => (
                    <th key={d}>{d.replace("_", " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(weights.weights)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([ticker, w]) => (
                    <tr key={ticker}>
                      <td className={styles.tickerCell}>{ticker}</td>
                      {DIMS.map((d) => {
                        const v = w[d] ?? 1.0;
                        return (
                          <td
                            className={v !== 1.0 ? styles.weightCellModified : undefined}
                            key={d}
                            style={{ color: weightColor(v) }}
                          >
                            {v.toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="section-title">Performance Reports ({entries.length})</div>
      {entries.length === 0 ? (
        <div className="empty-state">
          No performance reports yet. Analysis runs weekly on Fridays.
        </div>
      ) : (
        entries.map((entry, i) => (
          <div className="card markdown-body" key={i}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
          </div>
        ))
      )}
    </div>
  );
}
