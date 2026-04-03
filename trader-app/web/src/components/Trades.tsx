"use client";

import { useEffect, useState } from "react";
import { api, TradeEntry } from "@/lib/api";

export default function Trades() {
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTrades(100).then(setTrades).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading trades...</div>;
  if (trades.length === 0) return <div className="empty-state">No trades recorded yet.</div>;

  return (
    <div style={{ paddingBottom: "2rem" }}>
      <div className="section-title">Trade Log ({trades.length} entries)</div>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
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
                  key={i}
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  style={{ cursor: "pointer" }}
                  role="button"
                  aria-expanded={expanded === i}
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setExpanded(expanded === i ? null : i); }}
                >
                  <td style={{ fontSize: "0.8rem" }}>{trade.date || "—"}</td>
                  <td>
                    {trade.action === "BUY" && <span className="badge badge-green">BUY</span>}
                    {trade.action === "SELL" && <span className="badge badge-red">SELL</span>}
                    {trade.action === "NO_ACTION" && <span className="badge badge-gray">HOLD</span>}
                    {!trade.action && <span className="badge badge-gray">—</span>}
                  </td>
                  <td style={{ fontWeight: 600 }}>{trade.instrument || "—"}</td>
                  <td>{trade.quantity || "—"}</td>
                  <td>{trade.price || "—"}</td>
                  <td>{trade.realized_pnl || "—"}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{trade.portfolio_balance || "—"}</td>
                </tr>
                {expanded === i && (
                  <tr key={`${i}-detail`}>
                    <td colSpan={7} style={{ background: "var(--bg)", padding: "1rem" }}>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>Reasoning</div>
                      <div style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>
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
