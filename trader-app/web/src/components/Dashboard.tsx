"use client";

import { useEffect, useState } from "react";
import { api, Portfolio, TaskInfo } from "@/lib/api";
import { cronToHuman } from "@/lib/cron";
import PortfolioChart from "./PortfolioChart";
import IndexTracker from "./IndexTracker";

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [regime, setRegime] = useState<{ regime: string; parameters: Record<string, unknown> } | null>(null);
  const [error, setError] = useState("");
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  async function load() {
    try {
      const [p, t] = await Promise.all([api.getPortfolio(), api.getTasks()]);
      setPortfolio(p);
      setTasks(t);
      setLastFetched(new Date());
      setError("");
      // Regime is non-critical — don't let it break the dashboard
      try {
        const r = await api.getRegime();
        setRegime(r);
      } catch {
        setRegime(null);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  if (error) return <div className="card" style={{ color: "var(--red)" }}>Error: {error}</div>;
  if (!portfolio) return <div className="empty-state"><span className="spinner" /> Loading...</div>;

  const gainLoss = portfolio.total_value_usd - portfolio.starting_capital;
  const pctReturn = (gainLoss / portfolio.starting_capital) * 100;
  const isPositive = gainLoss >= 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingBottom: "2rem" }}>
      {/* Market Indices */}
      <IndexTracker />

      {/* Stats row */}
      <div className="grid-4">
        <div className="card">
          <div className="stat-label">Portfolio Value</div>
          <div className={`stat-value ${isPositive ? "positive" : "negative"}`}>
            ${portfolio.total_value_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Cash Available</div>
          <div className="stat-value">
            ${portfolio.cash_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Total Return</div>
          <div className={`stat-value ${isPositive ? "positive" : "negative"}`}>
            {isPositive ? "+" : ""}{pctReturn.toFixed(2)}%
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Market Regime</div>
          <div className="stat-value" style={{ fontSize: "1rem" }}>
            {regime ? (
              <span className={`badge ${
                regime.regime.includes("UPTREND") ? "badge-green" :
                regime.regime.includes("DOWNTREND") ? "badge-red" : "badge-yellow"
              }`}>
                {regime.regime}
              </span>
            ) : "—"}
          </div>
        </div>
      </div>

      {/* Performance band */}
      <div className="grid-3">
        <div className="card">
          <div className="stat-label">Gain / Loss</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 600, color: isPositive ? "var(--green)" : "var(--red)" }}>
            {isPositive ? "+" : ""}${gainLoss.toFixed(2)}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">All-Time High</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>${portfolio.all_time_high.toFixed(2)}</div>
        </div>
        <div className="card">
          <div className="stat-label">All-Time Low</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>${portfolio.all_time_low.toFixed(2)}</div>
        </div>
      </div>

      {/* Portfolio History Chart */}
      <PortfolioChart />

      {/* Open Positions */}
      <div className="card">
        <div className="section-title">Open Positions</div>
        {portfolio.positions.length === 0 ? (
          <div className="empty-state" style={{ padding: "1.5rem" }}>No open positions — all cash</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Type</th>
                <th>Qty</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Trailing Stop</th>
                <th>Unrealized P&amp;L</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((pos) => (
                <tr key={pos.ticker}>
                  <td style={{ fontWeight: 600 }}>{pos.ticker}</td>
                  <td><span className="badge badge-blue">{pos.instrument_type}</span></td>
                  <td>{pos.quantity}</td>
                  <td>${pos.entry_price.toFixed(2)}</td>
                  <td>${pos.current_price.toFixed(2)}</td>
                  <td style={{ color: "var(--yellow)", fontSize: "0.85rem" }}>
                    {pos.trailing_stop != null ? `$${pos.trailing_stop.toFixed(2)}` : "—"}
                    {pos.take_profit_partial_hit && " (50% taken)"}
                  </td>
                  <td style={{ color: pos.unrealized_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                    {pos.unrealized_pnl >= 0 ? "+" : ""}${pos.unrealized_pnl.toFixed(2)}
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {pos.notes}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Task Status */}
      <div className="card">
        <div className="section-title">Scheduled Tasks</div>
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>Schedule</th>
              <th>Status</th>
              <th>Last Run</th>
              <th>Finished</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.task_id}>
                <td style={{ fontWeight: 600 }}>{task.name}</td>
                <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{cronToHuman(task.cron)}</td>
                <td>
                  {task.is_running ? (
                    <span className="badge badge-yellow">Running <span className="spinner" style={{ marginLeft: 4 }} /></span>
                  ) : (
                    <span className="badge badge-green">Idle</span>
                  )}
                </td>
                <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {task.last_run ? new Date(task.last_run.started_at).toLocaleString() : "Never"}
                </td>
                <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {task.last_run?.finished_at ? new Date(task.last_run.finished_at).toLocaleString() : "—"}
                </td>
                <td>
                  {task.last_run ? (
                    <span className={`badge ${task.last_run.status === "completed" ? "badge-green" : task.last_run.status === "failed" ? "badge-red" : "badge-yellow"}`}>
                      {task.last_run.status}
                    </span>
                  ) : (
                    <span className="badge badge-gray">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
        Last updated: {lastFetched ? lastFetched.toLocaleString() : "—"} · Auto-refreshes every 30s
      </div>
    </div>
  );
}
