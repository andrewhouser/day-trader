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

const TOOLTIPS: Record<string, string> = {
  VIX: "CBOE Volatility Index — measures expected 30-day S&P 500 volatility. Above 20 signals fear, below 15 signals complacency.",
  "SPY RSI": "Relative Strength Index for SPY over 14 periods. Above 70 is overbought, below 30 is oversold.",
  "SPY ROC(20d)": "Rate of Change — SPY's percentage price change over the last 20 trading days.",
  "SMA 50/200": "50-day vs 200-day Simple Moving Average crossover. Golden Cross (50 > 200) is bullish, Death Cross is bearish.",
  Ticker: "The ETF or instrument symbol.",
  Price: "Latest market price.",
  "SMA 20": "Simple Moving Average over 20 days — short-term trend direction.",
  "SMA 50": "Simple Moving Average over 50 days — medium-term trend direction.",
  "SMA 200": "Simple Moving Average over 200 days — long-term trend direction.",
  RSI: "Relative Strength Index (14-period). Above 70 is overbought, below 30 is oversold.",
  "MACD Hist": "MACD Histogram — difference between the MACD line and signal line. Positive is bullish momentum, negative is bearish.",
  ATR: "Average True Range (14-period) — measures daily price volatility in dollar terms.",
  "BB Low": "Bollinger Band lower bound (SMA 20 − 2 std dev). Price near this level may be oversold.",
  "BB High": "Bollinger Band upper bound (SMA 20 + 2 std dev). Price near this level may be overbought.",
  "Vol Ratio": "Volume Ratio — today's volume divided by the 20-day average. Above 1 means higher-than-normal activity.",
  "ROC 20d": "Rate of Change — percentage price change over the last 20 trading days.",
};

function Tip({ label }: { label: string }) {
  const tip = TOOLTIPS[label];
  if (!tip) return <>{label}</>;
  return (
    <span className="tip-wrapper">
      {label}
      <span className="tip-bubble">{tip}</span>
    </span>
  );
}

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
            {regime.signals.vix != null && <span><Tip label="VIX" />: {String(regime.signals.vix)}</span>}
            {regime.signals.rsi != null && <span><Tip label="SPY RSI" />: {String(regime.signals.rsi)}</span>}
            {regime.signals.roc_20 != null && <span><Tip label="SPY ROC(20d)" />: {String(regime.signals.roc_20)}%</span>}
            <span><Tip label="SMA 50/200" />: {regime.signals.golden_cross ? "Golden Cross ✅" : "Death Cross ❌"}</span>
          </div>
        </div>
      )}

      <div className="card">
        <div className="section-title">Technical Indicators</div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th><Tip label="Ticker" /></th>
                <th><Tip label="Price" /></th>
                <th><Tip label="SMA 20" /></th>
                <th><Tip label="SMA 50" /></th>
                <th><Tip label="SMA 200" /></th>
                <th><Tip label="RSI" /></th>
                <th><Tip label="MACD Hist" /></th>
                <th><Tip label="ATR" /></th>
                <th><Tip label="BB Low" /></th>
                <th><Tip label="BB High" /></th>
                <th><Tip label="Vol Ratio" /></th>
                <th><Tip label="ROC 20d" /></th>
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
