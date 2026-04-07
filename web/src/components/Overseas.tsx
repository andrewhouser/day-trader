"use client";

import { useEffect, useState } from "react";

import ReactMarkdown from "react-markdown";

import remarkGfm from "remark-gfm";

import { api, OverseasSignal } from "@/lib/api";

import styles from "./Overseas.module.css";

type MonitorTab = "handoff" | "nikkei" | "ftse";

export function Overseas() {
  const [tab, setTab] = useState<MonitorTab>("handoff");
  const [handoff, setHandoff] = useState<{ raw: string }[]>([]);
  const [nikkei, setNikkei] = useState<{ raw: string }[]>([]);
  const [ftse, setFtse] = useState<{ raw: string }[]>([]);
  const [pending, setPending] = useState<OverseasSignal[]>([]);
  const [evaluated, setEvaluated] = useState<OverseasSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getHandoffSummary(3).catch(() => []),
      api.getNikkeiMonitor(5).catch(() => []),
      api.getFtseMonitor(5).catch(() => []),
      api.getOverseasSignals().catch(() => ({ pending: [], evaluated: [], total: 0 })),
    ])
      .then(([h, n, f, s]) => {
        setHandoff(h);
        setNikkei(n);
        setFtse(f);
        setPending(s.pending);
        setEvaluated(s.evaluated);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading overseas data...
      </div>
    );
  }

  const noData = handoff.length === 0 && nikkei.length === 0 && ftse.length === 0;
  if (noData && pending.length === 0 && evaluated.length === 0) {
    return (
      <div className="empty-state">
        No overseas monitor data yet. The Nikkei monitor runs overnight (7–10:30 PM ET),
        the FTSE monitor runs early morning (2:30–5:30 AM ET), and the handoff summary
        is generated at 5:30 AM ET.
      </div>
    );
  }

  const entries = tab === "handoff" ? handoff : tab === "nikkei" ? nikkei : ftse;
  const emptyMsg =
    tab === "handoff"
      ? "No handoff summary yet. Generated at 5:30 AM ET."
      : tab === "nikkei"
        ? "No Nikkei monitor data yet. Runs 7–10:30 PM ET Sun–Thu."
        : "No FTSE monitor data yet. Runs 2:30–5:30 AM ET Mon–Fri.";

  return (
    <div className={styles.container}>
      <div className={styles.grid}>
        {/* Monitor entries panel */}
        <div>
          <div className={styles.tabBar}>
            <button
              className={`${styles.tab} ${tab === "handoff" ? styles.tabActive : ""}`}
              onClick={() => setTab("handoff")}
            >
              🌍 Handoff Summary
            </button>
            <button
              className={`${styles.tab} ${tab === "nikkei" ? styles.tabActive : ""}`}
              onClick={() => setTab("nikkei")}
            >
              🇯🇵 Nikkei
            </button>
            <button
              className={`${styles.tab} ${tab === "ftse" ? styles.tabActive : ""}`}
              onClick={() => setTab("ftse")}
            >
              🇬🇧 FTSE
            </button>
          </div>

          {entries.length === 0 ? (
            <div className="empty-state">{emptyMsg}</div>
          ) : (
            entries.map((entry, i) => (
              <div className="card markdown-body" key={i}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
              </div>
            ))
          )}
        </div>

        {/* Signals panel */}
        <div>
          <div className={styles.panelHeader}>
            <span className={styles.panelIcon}>📡</span>
            <span className={styles.panelTitle}>Trade Signals</span>
          </div>

          {pending.length > 0 && (
            <div className="card" style={{ marginBottom: "0.75rem" }}>
              <div className="section-title">
                Pending ({pending.length})
              </div>
              {pending.map((sig) => (
                <SignalRow key={sig.id} signal={sig} />
              ))}
            </div>
          )}

          {evaluated.length > 0 && (
            <div className="card">
              <div className="section-title">
                Evaluated ({evaluated.length})
              </div>
              {evaluated.map((sig) => (
                <SignalRow key={sig.id} signal={sig} />
              ))}
            </div>
          )}

          {pending.length === 0 && evaluated.length === 0 && (
            <div className="card">
              <div className={styles.emptySignals}>
                No trade signals. Signals are emitted when overseas monitors detect moves
                ≥1.5% in international ETFs (EWJ, EWU, EWG).
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SignalRow({ signal }: { signal: OverseasSignal }) {
  const isBullish = signal.direction === "bullish";
  const arrow = isBullish ? "▲" : "▼";
  const color = isBullish ? "var(--green)" : "var(--red)";
  const urgencyBadge =
    signal.urgency === "high" ? (
      <span className="badge badge-red" style={{ marginLeft: "0.4rem" }}>🔴 High</span>
    ) : null;

  const time = signal.created_at
    ? new Date(signal.created_at).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "";

  return (
    <div className={styles.signalCard}>
      <div className={styles.signalDirection} style={{ color }}>
        {arrow}
      </div>
      <div className={styles.signalBody}>
        <div>
          <span className={styles.signalTicker}>{signal.ticker}</span>
          <span className={styles.signalMove} style={{ color }}>
            {signal.move_pct > 0 ? "+" : ""}
            {signal.move_pct?.toFixed(1)}%
          </span>
          {urgencyBadge}
          {signal.suggested_action && (
            <span
              className={`badge ${isBullish ? "badge-green" : "badge-red"}`}
              style={{ marginLeft: "0.4rem" }}
            >
              {signal.suggested_action}
            </span>
          )}
        </div>
        {signal.driver && <div className={styles.signalDriver}>{signal.driver}</div>}
        <div className={styles.signalMeta}>
          {time}
          {signal.status === "evaluated" && signal.evaluated_at && " · Evaluated"}
        </div>
      </div>
    </div>
  );
}
