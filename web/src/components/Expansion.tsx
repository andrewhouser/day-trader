"use client";

import { useEffect, useState } from "react";

import { api, ExpansionProposal } from "@/lib/api";

import styles from "./Expansion.module.css";

type FilterStatus = "" | "approved" | "pending" | "rejected";

export function Expansion() {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterStatus>("");
  const [instruments, setInstruments] = useState<Record<string, { tracks: string; type: string }>>({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [proposals, setProposals] = useState<ExpansionProposal[]>([]);

  useEffect(() => {
    load();
  }, [filter]);

  async function handleApprove(id: string, ticker: string) {
    setActionLoading(id);
    try {
      await api.approveProposal(id);
      setMessage(`Approved ${ticker} — now tradeable`);
      await load();
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Failed to approve");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(id: string, ticker: string) {
    const reason = prompt(`Reason for rejecting ${ticker}? (optional)`);
    if (reason === null) return;
    setActionLoading(id);
    try {
      await api.rejectProposal(id, reason);
      setMessage(`Rejected ${ticker}`);
      await load();
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Failed to reject");
    } finally {
      setActionLoading(null);
    }
  }

  async function load() {
    setLoading(true);
    try {
      const [p, inst] = await Promise.all([
        api.getProposals(filter),
        api.getTradeableInstruments(),
      ]);
      const sorted = [...p].sort((a, b) => {
        if (a.status === "pending" && b.status !== "pending") return -1;
        if (a.status !== "pending" && b.status === "pending") return 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      setInstruments(inst);
      setMessage("");
      setProposals(sorted);
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  const pendingCount = proposals.filter((p) => p.status === "pending").length;

  return (
    <div className={styles.container}>
      {message && (
        <div
          className={`card ${message.includes("Failed") ? styles.messageError : styles.messageSuccess}`}
        >
          {message}
        </div>
      )}

      <div className="card">
        <div className="section-title">
          Tradeable Instruments ({Object.keys(instruments).length})
        </div>
        <div className={styles.instrumentsWrap}>
          {Object.entries(instruments).map(([ticker, info]) => (
            <span
              className={`badge ${info.type === "ETF" ? "badge-blue" : info.type === "Stock" ? "badge-green" : "badge-yellow"}`}
              key={ticker}
            >
              {ticker}{" "}
              <span className={styles.instrumentTypeSuffix}>({info.type})</span>
            </span>
          ))}
        </div>
      </div>

      <div className={styles.filterRow}>
        {(["", "approved", "pending", "rejected"] as FilterStatus[]).map((s) => (
          <button
            className={`badge ${filter === s ? "badge-blue" : "badge-gray"}`}
            key={s}
            onClick={() => setFilter(s)}
            style={{ border: "none", cursor: "pointer", fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
          >
            {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            {s === "pending" && pendingCount > 0 ? ` (${pendingCount})` : ""}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="empty-state">
          <span className="spinner" /> Loading proposals...
        </div>
      ) : proposals.length === 0 ? (
        <div className="empty-state">
          No {filter || ""} proposals yet. The expansion agent runs weekly to suggest new
          instruments, or you can trigger it manually from the Tasks page.
        </div>
      ) : (
        proposals.map((p) => (
          <div
            className="card"
            key={p.id}
            style={{
              borderLeft: `3px solid ${p.status === "pending" ? "var(--yellow)" : p.status === "approved" ? "var(--green)" : "var(--red)"}`,
            }}
          >
            <div className={styles.proposalHeader}>
              <div>
                <span className={styles.proposalTicker}>{p.ticker}</span>
                <span
                  className={`badge ${p.instrument_type === "Stock" ? "badge-green" : p.instrument_type.includes("Bond") || p.instrument_type.includes("Treasury") ? "badge-yellow" : "badge-blue"}`}
                >
                  {p.instrument_type}
                </span>
                <span className="badge badge-gray" style={{ marginLeft: "0.25rem" }}>
                  {p.region}
                </span>
                <span
                  className={`badge ${p.risk_level === "low" ? "badge-green" : p.risk_level === "high" ? "badge-red" : "badge-yellow"}`}
                  style={{ marginLeft: "0.25rem" }}
                >
                  {p.risk_level} risk
                </span>
              </div>
              <span
                className={`badge ${p.status === "pending" ? "badge-yellow" : p.status === "approved" ? "badge-green" : "badge-red"}`}
              >
                {p.status.toUpperCase()}
              </span>
            </div>

            <div className={styles.description}>{p.description}</div>

            {p.expected_return && (
              <div className={styles.expectedReturn}>
                <span className={styles.expectedReturnLabel}>Expected return:</span>{" "}
                {p.expected_return}
              </div>
            )}

            <div className={styles.rationale}>
              <span className={styles.rationaleLabel}>Rationale:</span> {p.rationale}
            </div>

            <div className={styles.proposalBottom}>
              <div className={styles.proposalMeta}>
                Proposed {new Date(p.created_at).toLocaleString()} by {p.source}
                {p.decided_at && ` · Decided ${new Date(p.decided_at).toLocaleString()}`}
                {p.rejection_reason && ` · Reason: ${p.rejection_reason}`}
              </div>

              {p.status === "pending" && (
                <div className={styles.proposalActions}>
                  <button
                    className={styles.approveButton}
                    disabled={actionLoading === p.id}
                    onClick={() => handleApprove(p.id, p.ticker)}
                  >
                    {actionLoading === p.id ? "..." : "Approve"}
                  </button>
                  <button
                    className={styles.rejectButton}
                    disabled={actionLoading === p.id}
                    onClick={() => handleReject(p.id, p.ticker)}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
