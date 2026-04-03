"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, ScoreWeightsResult } from "@/lib/api";

const DIMS = ["trend", "momentum", "sentiment", "risk_reward", "event_risk", "sector_divergence"];

function weightColor(v: number): string {
  if (v > 1.0) return "var(--green)";
  if (v < 1.0) return "var(--red)";
  return "var(--text-muted)";
}

export default function Performance() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [weights, setWeights] = useState<ScoreWeightsResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getPerformance(10).then(setEntries),
      api.getScoreWeights().then(setWeights).catch(() => null),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading performance...</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingBottom: "2rem" }}>
      {/* Score Weights */}
      {weights && Object.keys(weights.weights).length > 0 && (
        <>
          <div className="section-title">Score Dimension Weights</div>
          <div className="card" style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  {DIMS.map((d) => <th key={d}>{d.replace("_", " ")}</th>)}
                </tr>
              </thead>
              <tbody>
                {Object.entries(weights.weights).sort(([a], [b]) => a.localeCompare(b)).map(([ticker, w]) => (
                  <tr key={ticker}>
                    <td style={{ fontWeight: 600 }}>{ticker}</td>
                    {DIMS.map((d) => {
                      const v = w[d] ?? 1.0;
                      return (
                        <td key={d} style={{ color: weightColor(v), fontWeight: v !== 1.0 ? 600 : 400 }}>
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

      {/* Performance Reports */}
      <div className="section-title">Performance Reports ({entries.length})</div>
      {entries.length === 0 ? (
        <div className="empty-state">No performance reports yet. Analysis runs weekly on Fridays.</div>
      ) : (
        entries.map((entry, i) => (
          <div key={i} className="card markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
          </div>
        ))
      )}
    </div>
  );
}
