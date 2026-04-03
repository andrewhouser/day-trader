"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type TechnicalData = Record<string, Record<string, number | string | null>>;
type RegimeData = {
  regime: string;
  timestamp: string;
  signals: Record<string, unknown>;
  parameters: Record<string, unknown>;
};

export default function Technicals() {
  const [technicals, setTechnicals] = useState<TechnicalData | null>(null);
  const [regime, setRegime] = useState<RegimeData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const t = await api.getTechnicals();
      setTechnicals(t);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
    // Regime is non-critical — don't let it block the page
    try {
      const r = await api.getRegime();
      setRegime(r);
    } catch {
      setRegime(null);
    }
  }

  if (error) return <div className="card" style={{ color: "var(--red)" }}>Error: {error}</div>;
  if (!technicals) return <div className="empty-state"><span className="spinner" /> Loading technicals...</div>;

  const regimeColors: Record<string, string> = {
    STRONG_UPTREND: "var(--green)",
    UPTREND: "var(--green)",
    SIDEWAYS: "var(--yellow)",
    DOWNTREND: "var(--red)",
    STRONG_DOWNTREND: "var(--red)",
    HIGH_VOLATILITY: "var(--yellow)",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingBottom: "2rem" }}>
      {regime && (
        <div className="card">
          <div className="section-title">Market Regime</div>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <span className="badge" style={{
              background: regimeColors[regime.regime] || "var(--text-muted)",
              color: "#fff", fontSize: "1rem", padding: "0.4rem 1rem"
            }}>
              {regime.regime}
            </span>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              {(regime.parameters as Record<string, string>).strategy_note}
            </span>
          </div>
          <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
            {regime.signals.vix != null && <span>VIX: {String(regime.signals.vix)}</span>}
            {regime.signals.rsi != null && <span>SPY RSI: {String(regime.signals.rsi)}</span>}
            {regime.signals.roc_20 != null && <span>SPY ROC(20d): {String(regime.signals.roc_20)}%</span>}
            <span>SMA 50/200: {regime.signals.golden_cross ? "Golden Cross ✅" : "Death Cross ❌"}</span>
          </div>
        </div>
      )}

      <div className="card">
        <div className="section-title">Technical Indicators</div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Price</th>
                <th>SMA 20</th>
                <th>SMA 50</th>
                <th>SMA 200</th>
                <th>RSI</th>
                <th>MACD Hist</th>
                <th>ATR</th>
                <th>BB Low</th>
                <th>BB High</th>
                <th>Vol Ratio</th>
                <th>ROC 20d</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(technicals).map(([ticker, data]) => {
                if (data.error) return (
                  <tr key={ticker}>
                    <td style={{ fontWeight: 600 }}>{ticker}</td>
                    <td colSpan={11} style={{ color: "var(--text-muted)" }}>{String(data.error)}</td>
                  </tr>
                );
                const rsi = data.rsi_14 as number | null;
                const rsiColor = rsi != null ? (rsi > 70 ? "var(--red)" : rsi < 30 ? "var(--green)" : "inherit") : "inherit";
                const macdH = data.macd_histogram as number | null;
                const macdColor = macdH != null ? (macdH > 0 ? "var(--green)" : "var(--red)") : "inherit";
                return (
                  <tr key={ticker}>
                    <td style={{ fontWeight: 600 }}>{ticker}</td>
                    <td>${data.price ?? "—"}</td>
                    <td>{data.sma_20 ?? "—"}</td>
                    <td>{data.sma_50 ?? "—"}</td>
                    <td>{data.sma_200 ?? "—"}</td>
                    <td style={{ color: rsiColor }}>{rsi?.toFixed(1) ?? "—"}</td>
                    <td style={{ color: macdColor }}>{macdH?.toFixed(4) ?? "—"}</td>
                    <td>{data.atr_14 ?? "—"}</td>
                    <td>{data.bb_lower ?? "—"}</td>
                    <td>{data.bb_upper ?? "—"}</td>
                    <td>{data.volume_ratio ?? "—"}</td>
                    <td style={{ color: (data.roc_20 as number) > 0 ? "var(--green)" : "var(--red)" }}>
                      {data.roc_20 != null ? `${data.roc_20}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <button onClick={load} style={{ alignSelf: "center", padding: "0.5rem 1.5rem", cursor: "pointer" }}>
        Refresh
      </button>
    </div>
  );
}
