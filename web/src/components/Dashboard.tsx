"use client";

import { useEffect, useState } from "react";

import { api, Portfolio, Position, TaskInfo } from "@/lib/api";
import { groupTasksByCategory } from "@/lib/constants";
import { cronToHuman } from "@/lib/cron";

import { PortfolioChart } from "./PortfolioChart";
import { PositionChart } from "./PositionChart";

import styles from "./Dashboard.module.css";

export function Dashboard() {
  const [error, setError] = useState("");
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [regime, setRegime] = useState<{
    parameters: Record<string, unknown>;
    regime: string;
  } | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [tasks, setTasks] = useState<TaskInfo[]>([]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  async function load() {
    try {
      const [p, t] = await Promise.all([api.getPortfolio(), api.getTasks()]);
      setError("");
      setLastFetched(new Date());
      setPortfolio(p);
      setTasks(t);
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

  if (error) {
    return <div className={`card ${styles.errorCard}`}>Error: {error}</div>;
  }
  if (!portfolio) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading...
      </div>
    );
  }

  const gainLoss = portfolio.total_value_usd - portfolio.starting_capital;
  const isPositive = gainLoss >= 0;
  const pctReturn = (gainLoss / portfolio.starting_capital) * 100;

  return (
    <div className={styles.container}>
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
            {isPositive ? "+" : ""}
            {pctReturn.toFixed(2)}%
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Market Regime</div>
          <div className={`stat-value ${styles.regimeValue}`}>
            {regime ? (
              <span
                className={`badge ${
                  regime.regime.includes("UPTREND")
                    ? "badge-green"
                    : regime.regime.includes("DOWNTREND")
                      ? "badge-red"
                      : "badge-yellow"
                }`}
              >
                {regime.regime}
              </span>
            ) : (
              "—"
            )}
          </div>
        </div>
      </div>

      <div className="grid-3">
        <div className="card">
          <div className="stat-label">Gain / Loss</div>
          <div
            className={isPositive ? styles.gainLossValuePositive : styles.gainLossValueNegative}
          >
            {isPositive ? "+" : ""}${gainLoss.toFixed(2)}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">All-Time High</div>
          <div className={styles.statValueLarge}>${portfolio.all_time_high.toFixed(2)}</div>
        </div>
        <div className="card">
          <div className="stat-label">All-Time Low</div>
          <div className={styles.statValueLarge}>${portfolio.all_time_low.toFixed(2)}</div>
        </div>
      </div>

      <PortfolioChart />

      <div className="card">
        <div className="section-title">Open Positions</div>
        {portfolio.positions.length === 0 ? (
          <div className="empty-state" style={{ padding: "1.5rem" }}>
            No open positions — all cash
          </div>
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
                <tr
                  className={styles.clickableRow}
                  key={pos.ticker}
                  onClick={() => setSelectedPosition(pos)}
                >
                  <td style={{ fontWeight: 600 }}>{pos.ticker}</td>
                  <td>
                    <span className="badge badge-blue">{pos.instrument_type}</span>
                  </td>
                  <td>{typeof pos.quantity === 'number' ? (Number.isInteger(pos.quantity) ? pos.quantity : pos.quantity.toFixed(3)) : pos.quantity}</td>
                  <td>${pos.entry_price.toFixed(2)}</td>
                  <td>${pos.current_price.toFixed(2)}</td>
                  <td className={styles.trailingStopCell}>
                    {pos.trailing_stop != null ? `$${pos.trailing_stop.toFixed(2)}` : "—"}
                    {pos.take_profit_partial_hit && " (50% taken)"}
                  </td>
                  <td className={pos.unrealized_pnl >= 0 ? styles.pnlCellPositive : styles.pnlCellNegative}>
                    {pos.unrealized_pnl >= 0 ? "+" : ""}${pos.unrealized_pnl.toFixed(2)}
                  </td>
                  <td className={styles.notesCell}>{pos.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

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
            {Object.entries(groupTasksByCategory(tasks)).map(([category, categoryTasks]) => (
              <>
                <tr key={`cat-${category}`}>
                  <td className={styles.categoryRow} colSpan={6}>{category}</td>
                </tr>
                {categoryTasks.map((task) => (
              <tr key={task.task_id}>
                <td className={styles.taskName}>{task.name}</td>
                <td className={styles.taskSchedule}>{cronToHuman(task.cron)}</td>
                <td>
                  {task.is_running ? (
                    <span className="badge badge-yellow">
                      Running <span className="spinner" style={{ marginLeft: 4 }} />
                    </span>
                  ) : (
                    <span className="badge badge-green">Idle</span>
                  )}
                </td>
                <td className={styles.smallDateCell}>
                  {task.last_run
                    ? new Date(task.last_run.started_at).toLocaleString()
                    : "Never"}
                </td>
                <td className={styles.smallDateCell}>
                  {task.last_run?.finished_at
                    ? new Date(task.last_run.finished_at).toLocaleString()
                    : "—"}
                </td>
                <td>
                  {task.last_run ? (
                    <span
                      className={`badge ${task.last_run.status === "completed" ? "badge-green" : task.last_run.status === "failed" || task.last_run.status === "cancelled" ? "badge-red" : "badge-yellow"}`}
                    >
                      {task.last_run.status}
                    </span>
                  ) : (
                    <span className="badge badge-gray">—</span>
                  )}
                </td>
              </tr>
                ))}
              </>
            ))}
          </tbody>
        </table>
      </div>

      <div className={styles.timestamp}>
        Last updated: {lastFetched ? lastFetched.toLocaleString() : "—"} · Auto-refreshes
        every 30s
      </div>

      {selectedPosition && (
        <PositionChart
          entryPrice={selectedPosition.entry_price}
          onClose={() => setSelectedPosition(null)}
          ticker={selectedPosition.ticker}
          trailingStop={selectedPosition.trailing_stop}
        />
      )}
    </div>
  );
}
