"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { api, TickerSnapshot } from "@/lib/api";

const RANGES = [
  { label: "1D", days: 1 },
  { label: "7D", days: 7 },
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "6M", days: 180 },
  { label: "1Y", days: 365 },
] as const;

function formatTick(iso: string, days: number) {
  const d = new Date(iso);
  if (days <= 1) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (days <= 30) return d.toLocaleDateString([], { month: "short", day: "numeric" });
  return d.toLocaleDateString([], { month: "short", year: "2-digit" });
}

interface Props {
  ticker: string;
  entryPrice: number;
  trailingStop?: number | null;
  onClose: () => void;
}

export default function PositionChart({ ticker, entryPrice, trailingStop, onClose }: Props) {
  const [range, setRange] = useState(30);
  const [data, setData] = useState<TickerSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    api.getTickerHistory(ticker, range)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [ticker, range]);

  const chartData = data.map((s) => ({
    time: s.time,
    Price: s.price,
    High: s.high,
    Low: s.low,
  }));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: 720, padding: "1.25rem" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div style={{ fontWeight: 700, fontSize: "1.1rem" }}>{ticker} Price History</div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "1.2rem", cursor: "pointer" }} aria-label="Close">✕</button>
        </div>

        <div style={{ display: "flex", gap: "0.35rem", marginBottom: "0.75rem" }}>
          {RANGES.map((r) => (
            <button
              key={r.days}
              onClick={() => setRange(r.days)}
              className={`badge ${range === r.days ? "badge-blue" : "badge-gray"}`}
              style={{ cursor: "pointer", padding: "0.3rem 0.6rem", border: "none", fontSize: "0.8rem" }}
            >
              {r.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="empty-state" style={{ height: 260 }}><span className="spinner" /> Loading...</div>
        ) : error ? (
          <div className="empty-state" style={{ height: 260, color: "var(--red)" }}>{error}</div>
        ) : chartData.length === 0 ? (
          <div className="empty-state" style={{ height: 260 }}>No data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="gradPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--blue)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="time"
                tickFormatter={(v) => formatTick(v, range)}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                stroke="rgba(255,255,255,0.1)"
              />
              <YAxis
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                stroke="rgba(255,255,255,0.1)"
                tickFormatter={(v: number) => `$${v.toFixed(2)}`}
                domain={["auto", "auto"]}
              />
              <Tooltip
                contentStyle={{ background: "#1e1e2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 13 }}
                labelFormatter={(v) => new Date(v as string).toLocaleString()}
                formatter={(v) => [`$${Number(v).toFixed(2)}`]}
              />
              <ReferenceLine y={entryPrice} stroke="var(--green)" strokeDasharray="4 4" label={{ value: `Entry $${entryPrice.toFixed(2)}`, fill: "var(--green)", fontSize: 11, position: "right" }} />
              {trailingStop != null && (
                <ReferenceLine y={trailingStop} stroke="var(--red)" strokeDasharray="4 4" label={{ value: `Stop $${trailingStop.toFixed(2)}`, fill: "var(--red)", fontSize: 11, position: "right" }} />
              )}
              <Area type="monotone" dataKey="Price" stroke="var(--blue)" fill="url(#gradPrice)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}

        {!loading && data.length > 0 && (
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textAlign: "right", marginTop: "0.35rem" }}>
            {data.length} data point{data.length !== 1 ? "s" : ""}
          </div>
        )}
      </div>
    </div>
  );
}
