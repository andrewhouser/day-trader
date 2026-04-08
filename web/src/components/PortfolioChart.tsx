"use client";

import { useEffect, useState } from "react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, PortfolioSnapshot } from "@/lib/api";

import styles from "./PortfolioChart.module.css";

const RANGES = [
  { days: 1, label: "1D" },
  { days: 7, label: "7D" },
  { days: 30, label: "1M" },
  { days: 90, label: "3M" },
  { days: 180, label: "6M" },
  { days: 365, label: "1Y" },
] as const;

function describeSpan(data: PortfolioSnapshot[]): string {
  if (data.length === 0) return "";
  const diffMs =
    new Date(data[data.length - 1].timestamp).getTime() -
    new Date(data[0].timestamp).getTime();
  const diffMins = Math.round(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}m of data`;
  const diffHours = Math.round(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h of data`;
  return `${Math.round(diffHours / 24)}d of data`;
}

function formatTick(iso: string, days: number) {
  const d = new Date(iso);
  if (days <= 1) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (days <= 30) return d.toLocaleDateString([], { day: "numeric", month: "short" });
  return d.toLocaleDateString([], { month: "short", year: "2-digit" });
}

const STORAGE_KEY = "portfolioChartRange";

function getSavedRange(): number {
  if (typeof window === "undefined") return 30;
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    const n = Number(saved);
    if (RANGES.some((r) => r.days === n)) return n;
  }
  return 30;
}

export function PortfolioChart() {
  const [data, setData] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState(getSavedRange);

  function changeRange(days: number) {
    setRange(days);
    localStorage.setItem(STORAGE_KEY, String(days));
  }

  useEffect(() => {
    setLoading(true);
    api.getPortfolioHistory(range).then(setData).finally(() => setLoading(false));
  }, [range]);

  const chartData = data.map((s) => ({
    Cash: s.cash_usd,
    "Portfolio Value": s.total_value_usd,
    time: s.timestamp,
  }));

  const selectedLabel = RANGES.find((r) => r.days === range)?.label ?? "";
  const spanText = describeSpan(data);
  const dataSpanInsufficient =
    data.length > 0 &&
    (() => {
      const spanDays =
        (new Date(data[data.length - 1].timestamp).getTime() -
          new Date(data[0].timestamp).getTime()) /
        86400000;
      return spanDays < range * 0.5;
    })();

  return (
    <div className="card">
      <div className={styles.chartHeader}>
        <div className={styles.chartTitle}>
          <div className={`section-title ${styles.sectionTitleInline}`}>Portfolio History</div>
          {!loading && data.length > 0 && dataSpanInsufficient && (
            <span className={styles.insufficientDataNote}>
              ({spanText} available for {selectedLabel} view)
            </span>
          )}
        </div>
        <div className={styles.rangeButtons}>
          {RANGES.map((r) => (
            <button
              className={`badge ${range === r.days ? "badge-blue" : "badge-gray"} ${styles.rangeButton}`}
              key={r.days}
              onClick={() => changeRange(r.days)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className={`empty-state ${styles.emptyChart}`}>
          <span className="spinner" /> Loading chart...
        </div>
      ) : chartData.length === 0 ? (
        <div className={`empty-state ${styles.emptyChart}`}>
          No history data for the {selectedLabel} range. Data is recorded each time the agent
          runs.
        </div>
      ) : (
        <ResponsiveContainer height={280} width="100%">
          <AreaChart data={chartData} margin={{ bottom: 0, left: 10, right: 10, top: 5 }}>
            <defs>
              <linearGradient id="gradValue" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="var(--green)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradCash" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="var(--blue)" stopOpacity={0.2} />
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
              tickFormatter={(v: number) => `$${v.toLocaleString()}`}
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
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area
              dataKey="Portfolio Value"
              dot={false}
              fill="url(#gradValue)"
              stroke="var(--green)"
              strokeWidth={2}
              type="monotone"
            />
            <Area
              dataKey="Cash"
              dot={false}
              fill="url(#gradCash)"
              stroke="var(--blue)"
              strokeWidth={1.5}
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
  );
}
