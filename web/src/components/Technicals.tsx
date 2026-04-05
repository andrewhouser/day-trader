"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

import { Tip } from "./Tip";

import styles from "./Technicals.module.css";

type RegimeData = {
  parameters: Record<string, unknown>;
  regime: string;
  signals: Record<string, unknown>;
  timestamp: string;
};
type TechnicalData = Record<string, Record<string, number | string | null>>;

const TOOLTIPS: Record<string, string> = {
  ATR: "Average True Range (14-period) — measures daily price volatility in dollar terms.",
  "BB High":
    "Bollinger Band upper bound (SMA 20 + 2 std dev). Price near this level may be overbought.",
  "BB Low":
    "Bollinger Band lower bound (SMA 20 − 2 std dev). Price near this level may be oversold.",
  "MACD Hist":
    "MACD Histogram — difference between the MACD line and signal line. Positive is bullish momentum, negative is bearish.",
  Price: "Latest market price.",
  RSI: "Relative Strength Index (14-period). Above 70 is overbought, below 30 is oversold.",
  "ROC 20d": "Rate of Change — percentage price change over the last 20 trading days.",
  "SMA 20": "Simple Moving Average over 20 days — short-term trend direction.",
  "SMA 200": "Simple Moving Average over 200 days — long-term trend direction.",
  "SMA 50": "Simple Moving Average over 50 days — medium-term trend direction.",
  "SMA 50/200":
    "50-day vs 200-day Simple Moving Average crossover. Golden Cross (50 > 200) is bullish, Death Cross is bearish.",
  "SPY ROC(20d)": "Rate of Change — SPY's percentage price change over the last 20 trading days.",
  "SPY RSI":
    "Relative Strength Index for SPY over 14 periods. Above 70 is overbought, below 30 is oversold.",
  Ticker: "The ETF or instrument symbol.",
  VIX: "CBOE Volatility Index — measures expected 30-day S&P 500 volatility. Above 20 signals fear, below 15 signals complacency.",
  "Vol Ratio":
    "Volume Ratio — today's volume divided by the 20-day average. Above 1 means higher-than-normal activity.",
};

const REGIME_COLORS: Record<string, string> = {
  DOWNTREND: "var(--red)",
  HIGH_VOLATILITY: "var(--yellow)",
  SIDEWAYS: "var(--yellow)",
  STRONG_DOWNTREND: "var(--red)",
  STRONG_UPTREND: "var(--green)",
  UPTREND: "var(--green)",
};

export function Technicals() {
  const [error, setError] = useState("");
  const [regime, setRegime] = useState<RegimeData | null>(null);
  const [technicals, setTechnicals] = useState<TechnicalData | null>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const t = await api.getTechnicals();
      setError("");
      setTechnicals(t);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
    try {
      const r = await api.getRegime();
      setRegime(r);
    } catch {
      setRegime(null);
    }
  }

  if (error) {
    return <div className={`card ${styles.errorCard}`}>Error: {error}</div>;
  }
  if (!technicals) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading technicals...
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {regime && (
        <div className="card">
          <div className="section-title">Market Regime</div>
          <div className={styles.regimeRow}>
            <span
              className={`badge ${styles.regimeBadge}`}
              style={{
                background: REGIME_COLORS[regime.regime] || "var(--text-muted)",
                color: "#fff",
              }}
            >
              {regime.regime}
            </span>
            <span className={styles.regimeStrategyNote}>
              {(regime.parameters as Record<string, string>).strategy_note}
            </span>
          </div>
          <div className={styles.regimeSignals}>
            {regime.signals.vix != null && (
              <span>
                <Tip label="VIX" tooltips={TOOLTIPS} />: {String(regime.signals.vix)}
              </span>
            )}
            {regime.signals.rsi != null && (
              <span>
                <Tip label="SPY RSI" tooltips={TOOLTIPS} />: {String(regime.signals.rsi)}
              </span>
            )}
            {regime.signals.roc_20 != null && (
              <span>
                <Tip label="SPY ROC(20d)" tooltips={TOOLTIPS} />:{" "}
                {String(regime.signals.roc_20)}%
              </span>
            )}
            <span>
              <Tip label="SMA 50/200" tooltips={TOOLTIPS} />:{" "}
              {regime.signals.golden_cross ? "Golden Cross ✅" : "Death Cross ❌"}
            </span>
          </div>
        </div>
      )}

      <div className="card">
        <div className="section-title">Technical Indicators</div>
        <div className={styles.overflowX}>
          <table>
            <thead>
              <tr>
                <th>
                  <Tip label="Ticker" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="Price" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="SMA 20" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="SMA 50" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="SMA 200" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="RSI" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="MACD Hist" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="ATR" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="BB Low" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="BB High" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="Vol Ratio" tooltips={TOOLTIPS} />
                </th>
                <th>
                  <Tip label="ROC 20d" tooltips={TOOLTIPS} />
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(technicals).map(([ticker, data]) => {
                if (data.error) {
                  return (
                    <tr key={ticker}>
                      <td style={{ fontWeight: 600 }}>{ticker}</td>
                      <td colSpan={11} style={{ color: "var(--text-muted)" }}>
                        {String(data.error)}
                      </td>
                    </tr>
                  );
                }
                const macdH = data.macd_histogram as number | null;
                const rsi = data.rsi_14 as number | null;
                const macdColor =
                  macdH != null ? (macdH > 0 ? "var(--green)" : "var(--red)") : "inherit";
                const rsiColor =
                  rsi != null
                    ? rsi > 70
                      ? "var(--red)"
                      : rsi < 30
                        ? "var(--green)"
                        : "inherit"
                    : "inherit";
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
                    <td
                      style={{
                        color: (data.roc_20 as number) > 0 ? "var(--green)" : "var(--red)",
                      }}
                    >
                      {data.roc_20 != null ? `${data.roc_20}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <button className={styles.refreshButton} onClick={load}>
        Refresh
      </button>
    </div>
  );
}
