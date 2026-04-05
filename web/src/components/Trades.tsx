"use client";

import { useEffect, useState } from "react";

import { api, TradeEntry } from "@/lib/api";

import styles from "./Trades.module.css";

export function Trades() {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [trades, setTrades] = useState<TradeEntry[]>([]);

  useEffect(() => {
    api
      .getTrades(100)
      .then(setTrades)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading trades...
      </div>
    );
  }
  if (trades.length === 0) {
    return <div className="empty-state">No trades recorded yet.</div>;
  }

  return (
    <div className={styles.container}>
      <div className="section-title">Trade Log ({trades.length} entries)</div>
      <div className={`card ${styles.tableCard}`}>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Action</th>
              <th>Instrument</th>
              <th>Qty</th>
              <th>Price</th>
              <th>P&amp;L</th>
              <th>Balance</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, i) => (
              <>
                <tr
                  aria-expanded={expanded === i}
                  className={styles.clickableRow}
                  key={i}
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ")
                      setExpanded(expanded === i ? null : i);
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <td className={styles.dateCell}>{trade.date || "—"}</td>
                  <td>
                    {trade.action === "BUY" && (
                      <span className="badge badge-green">BUY</span>
                    )}
                    {trade.action === "SELL" && (
                      <span className="badge badge-red">SELL</span>
                    )}
                    {trade.action === "NO_ACTION" && (
                      <span className="badge badge-gray">HOLD</span>
                    )}
                    {!trade.action && <span className="badge badge-gray">—</span>}
                  </td>
                  <td className={styles.instrumentCell}>{trade.instrument || "—"}</td>
                  <td>{trade.quantity || "—"}</td>
                  <td>{trade.price || "—"}</td>
                  <td>{trade.realized_pnl || "—"}</td>
                  <td className={styles.balanceCell}>{trade.portfolio_balance || "—"}</td>
                </tr>
                {expanded === i && (
                  <tr key={`${i}-detail`}>
                    <td className={styles.detailCell} colSpan={7}>
                      <div className={styles.detailLabel}>Reasoning</div>
                      <div className={styles.detailContent}>
                        {trade.reasoning || trade.raw}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
