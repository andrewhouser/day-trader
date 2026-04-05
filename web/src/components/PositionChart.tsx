"use client";

import { useEffect, useState } from "react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, TickerSnapshot } from "@/lib/api";

import styles from "./PositionChart.module.css";

const RANGES = [
  { days: 1, label: "1D" },
  { days: 7, label: "7D" },
  { days: 30, label: "1M" },
  { days: 90, label: "3M" },
  { days: 180, label: "6M" },
  { days: 365, label: "1Y" },
] as const;

function formatTick(iso: string, days: number) {
  const d = new Date(iso);
  if (days <= 1) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (days <= 30) return d.toLocaleDateString([], { day: "numeric", month: "short" });
  return d.toLocaleDateString([], { month: "short", year: "2-digit" });
}

interface Props {
  entryPrice: number;
  onClose: () => void;
  ticker: string;
  trailingStop?: number | null;
}

export function PositionChart({ entryPrice, onClose, ticker, trailingStop }: Props) {
  const [data, setData] = useState<TickerSnapshot[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState(30);

  useEffect(() => {
    setError("");
    setLoading(true);
    api
      .getTickerHistory(ticker, range)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [ticker, range]);

  const chartData = data.map((s) => ({
    High: s.high,
    Low: s.low,
    Price: s.price,
    time: s.time,
  }));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={`modal-content ${styles.modalContent}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.modalHeader}>
          <div className={styles.modalTitle}>{ticker} Price History</div>
          <button
            aria-label="Close"
            className={styles.closeButton}
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <div className={styles.rangeButtons}>
          {RANGES.map((r) => (
            <button
              className={`badge ${range === r.days ? "badge-blue" : "badge-gray"} ${styles.rangeButton}`}
              key={r.days}
              onClick={() => setRange(r.days)}
            >
              {r.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className={`empty-state ${styles.emptyChart}`}>
            <span className="spinner" /> Loading...
          </div>
        ) : error ? (
          <div className={`empty-state ${styles.errorChart}`}>{error}</div>
        ) : chartData.length === 0 ? (
          <div className={`empty-state ${styles.emptyChart}`}>No data available</div>
        ) : (
          <ResponsiveContainer height={300} width="100%">
            <AreaChart data={chartData} margin={{ bottom: 0, left: 10, right: 10, top: 5 }}>
              <defs>
                <linearGradient id="gradPrice" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor="var(--blue)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                stroke="rgba(255,255,255,0.1)"
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickFormatter={(v) => formatTick(v, range)}
              />
              <YAxis
                domain={["auto", "auto"]}
                stroke="rgba(255,255,255,0.1)"
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickFormatter={(v: number) => `$${v.toFixed(2)}`}
              />
              <Tooltip
                contentStyle={{
                  background: "#1e1e2e",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 6,
                  fontSize: 13,
                }}
                formatter={(v) => [`$${Number(v).toFixed(2)}`]}
                labelFormatter={(v) => new Date(v as string).toLocaleString()}
              />
              <ReferenceLine
                label={{
                  fill: "var(--green)",
                  fontSize: 11,
                  position: "right",
                  value: `Entry $${entryPrice.toFixed(2)}`,
                }}
                stroke="var(--green)"
                strokeDasharray="4 4"
                y={entryPrice}
              />
              {trailingStop != null && (
                <ReferenceLine
                  label={{
                    fill: "var(--red)",
                    fontSize: 11,
                    position: "right",
                    value: `Stop $${trailingStop.toFixed(2)}`,
                  }}
                  stroke="var(--red)"
                  strokeDasharray="4 4"
                  y={trailingStop}
                />
              )}
              <Area
                dataKey="Price"
                dot={false}
                fill="url(#gradPrice)"
                stroke="var(--blue)"
                strokeWidth={2}
                type="monotone"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}

        {!loading && data.length > 0 && (
          <div className={styles.dataPointsLabel}>
            {data.length} data point{data.length !== 1 ? "s" : ""}
          </div>
        )}
      </div>
    </div>
  );
}
