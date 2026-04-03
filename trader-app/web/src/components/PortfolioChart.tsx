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
  Legend,
} from "recharts";
import { api, PortfolioSnapshot } from "@/lib/api";

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

export default function PortfolioChart() {
  const [range, setRange] = useState(30);
  const [data, setData] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getPortfolioHistory(range).then(setData).finally(() => setLoading(false));
  }, [range]);

  const chartData = data.map((s) => ({
    time: s.timestamp,
    "Portfolio Value": s.total_value_usd,
    Cash: s.cash_usd,
  }));

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div className="section-title" style={{ margin: 0 }}>Portfolio History</div>
        <div style={{ display: "flex", gap: "0.35rem" }}>
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
      </div>

      {loading ? (
        <div className="empty-state" style={{ height: 260 }}>
          <span className="spinner" /> Loading chart...
        </div>
      ) : chartData.length === 0 ? (
        <div className="empty-state" style={{ height: 260 }}>
          No history data for this range yet. Data is recorded each time the agent trades.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="gradValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--green)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradCash" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--blue)" stopOpacity={0.2} />
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
              tickFormatter={(v: number) => `$${v.toLocaleString()}`}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 13 }}
              labelFormatter={(v) => new Date(v as string).toLocaleString()}
              formatter={(v) => [`$${Number(v).toFixed(2)}`]}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area
              type="monotone"
              dataKey="Portfolio Value"
              stroke="var(--green)"
              fill="url(#gradValue)"
              strokeWidth={2}
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="Cash"
              stroke="var(--blue)"
              fill="url(#gradCash)"
              strokeWidth={1.5}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
