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

interface Metrics {
  total_trades: number;
  total_buys: number;
  total_sells: number;
  realized_trades: number;
  wins: number;
  losses: number;
  breakeven: number;
  win_rate: number;
  total_realized_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  portfolio_value: number;
  starting_capital: number;
  total_return_pct: number;
  all_time_high: number;
  all_time_low: number;
  max_drawdown_from_ath: number;
  by_instrument: Record<string, { trades: number; pnl: number }>;
  trade_details: { closed_count: number; patterns: string[] };
}

function parseReport(raw: string): { title: string; metrics: Metrics | null; analysis: string } {
  const titleMatch = raw.match(/^##\s+(.+)/m);
  const title = titleMatch ? titleMatch[1] : "Performance Report";

  // Extract JSON from the ```json ... ``` block
  let metrics: Metrics | null = null;
  const jsonMatch = raw.match(/```json\s*\n([\s\S]*?)\n```/);
  if (jsonMatch) {
    try {
      metrics = JSON.parse(jsonMatch[1]);
    } catch { /* ignore parse errors */ }
  }

  // Extract analysis (everything after ### Analysis)
  const analysisMatch = raw.match(/###\s*Analysis\s*\n([\s\S]*?)$/);
  const analysis = analysisMatch ? analysisMatch[1].trim() : "";

  return { title, metrics, analysis };
}

function MetricsSummary({ m }: { m: Metrics }) {
  const fmt = (n: number) => n.toFixed(2);
  const pct = (n: number) => `${n.toFixed(1)}%`;
  const usd = (n: number) => `$${n.toFixed(2)}`;

  return (
    <div className={styles.metricsGrid}>
      <div className={styles.metricCard}>
        <div className={styles.metricLabel}>Portfolio Value</div>
        <div className={styles.metricValue}>{usd(m.portfolio_value)}</div>
        <div className={styles.metricSub}>
          Return: <span style={{ color: m.total_return_pct >= 0 ? "var(--green)" : "var(--red)" }}>
            {pct(m.total_return_pct)}
          </span>
        </div>
      </div>
      <div className={styles.metricCard}>
        <div className={styles.metricLabel}>Trades</div>
        <div className={styles.metricValue}>{m.total_trades}</div>
        <div className={styles.metricSub}>{m.total_buys} buys · {m.total_sells} sells</div>
      </div>
      <div className={styles.metricCard}>
        <div className={styles.metricLabel}>Win Rate</div>
        <div className={styles.metricValue}>{m.realized_trades > 0 ? pct(m.win_rate) : "—"}</div>
        <div className={styles.metricSub}>{m.wins}W / {m.losses}L / {m.breakeven}B</div>
      </div>
      <div className={styles.metricCard}>
        <div className={styles.metricLabel}>Realized P&amp;L</div>
        <div className={styles.metricValue} style={{ color: m.total_realized_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
          {usd(m.total_realized_pnl)}
        </div>
        <div className={styles.metricSub}>Avg win: {usd(m.avg_win)} · Avg loss: {usd(m.avg_loss)}</div>
      </div>
      <div className={styles.metricCard}>
        <div className={styles.metricLabel}>Profit Factor</div>
        <div className={styles.metricValue}>{m.profit_factor === Infinity || m.profit_factor > 999 ? "∞" : fmt(m.profit_factor)}</div>
      </div>
      <div className={styles.metricCard}>
        <div className={styles.metricLabel}>Max Drawdown</div>
        <div className={styles.metricValue} style={{ color: m.max_drawdown_from_ath > 0 ? "var(--red)" : "var(--text-muted)" }}>
          {pct(m.max_drawdown_from_ath)}
        </div>
        <div className={styles.metricSub}>ATH: {usd(m.all_time_high)}</div>
      </div>
    </div>
  );
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
        entries.map((entry, i) => {
          const { title, metrics, analysis } = parseReport(entry.raw);
          const isError = analysis.startsWith("[ERROR]");

          return (
            <div className="card" key={i}>
              <div className={styles.reportTitle}>{title}</div>

              {metrics && <MetricsSummary m={metrics} />}

              {isError ? (
                <div className={styles.errorBanner}>
                  <span className={styles.errorIcon}>⚠</span>
                  LLM analysis unavailable — Ollama timed out or was unreachable.
                  <div className={styles.errorDetail}>{analysis}</div>
                </div>
              ) : analysis ? (
                <div className="markdown-body" style={{ marginTop: "1rem" }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis}</ReactMarkdown>
                </div>
              ) : null}

              {metrics && (
                <details className={styles.rawDetails}>
                  <summary>Raw metrics JSON</summary>
                  <pre className={styles.rawPre}>{JSON.stringify(metrics, null, 2)}</pre>
                </details>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
