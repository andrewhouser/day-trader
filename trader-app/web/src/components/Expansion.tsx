"use client";

import { useEffect, useState } from "react";
import { api, ExpansionProposal } from "@/lib/api";

type FilterStatus = "" | "pending" | "approved" | "rejected";

export default function Expansion() {
  const [proposals, setProposals] = useState<ExpansionProposal[]>([]);
  const [instruments, setInstruments] = useState<Record<string, { type: string; tracks: string }>>({});
  const [filter, setFilter] = useState<FilterStatus>("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    load();
  }, [filter]);

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
      setProposals(sorted);
      setInstruments(inst);
      setMessage("");
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

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
    if (reason === null) return; // cancelled
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

  const pendingCount = proposals.filter((p) => p.status === "pending").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingBottom: "2rem" }}>
      {message && (
        <div className="card" style={{ color: message.includes("Failed") ? "var(--red)" : "var(--green)", padding: "0.75rem 1rem" }}>
          {message}
        </div>
      )}

      {/* Current tradeable instruments */}
      <div className="card">
        <div className="section-title">Tradeable Instruments ({Object.keys(instruments).length})</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", padding: "0.5rem 0" }}>
          {Object.entries(instruments).map(([ticker, info]) => (
            <span key={ticker} className={`badge ${info.type === "ETF" ? "badge-blue" : info.type === "Stock" ? "badge-green" : "badge-yellow"}`}>
              {ticker} <span style={{ opacity: 0.7, fontSize: "0.75rem" }}>({info.type})</span>
            </span>
          ))}
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        {(["", "pending", "approved", "rejected"] as FilterStatus[]).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`badge ${filter === s ? "badge-blue" : "badge-gray"}`}
            style={{ cursor: "pointer", padding: "0.4rem 0.8rem", border: "none", fontSize: "0.85rem" }}
          >
            {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            {s === "pending" && pendingCount > 0 ? ` (${pendingCount})` : ""}
          </button>
        ))}
      </div>

      {/* Proposals */}
      {loading ? (
        <div className="empty-state"><span className="spinner" /> Loading proposals...</div>
      ) : proposals.length === 0 ? (
        <div className="empty-state">
          No {filter || ""} proposals yet. The expansion agent runs weekly to suggest new instruments,
          or you can trigger it manually from the Tasks page.
        </div>
      ) : (
        proposals.map((p) => (
          <div key={p.id} className="card" style={{ borderLeft: `3px solid ${p.status === "pending" ? "var(--yellow)" : p.status === "approved" ? "var(--green)" : "var(--red)"}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
              <div>
                <span style={{ fontWeight: 700, fontSize: "1.1rem", marginRight: "0.5rem" }}>{p.ticker}</span>
                <span className={`badge ${p.instrument_type === "Stock" ? "badge-green" : p.instrument_type.includes("Bond") || p.instrument_type.includes("Treasury") ? "badge-yellow" : "badge-blue"}`}>
                  {p.instrument_type}
                </span>
                <span className="badge badge-gray" style={{ marginLeft: "0.25rem" }}>{p.region}</span>
                <span className={`badge ${p.risk_level === "low" ? "badge-green" : p.risk_level === "high" ? "badge-red" : "badge-yellow"}`} style={{ marginLeft: "0.25rem" }}>
                  {p.risk_level} risk
                </span>
              </div>
              <span className={`badge ${p.status === "pending" ? "badge-yellow" : p.status === "approved" ? "badge-green" : "badge-red"}`}>
                {p.status.toUpperCase()}
              </span>
            </div>

            <div style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>{p.description}</div>

            {p.expected_return && (
              <div style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-muted)" }}>Expected return:</span> {p.expected_return}
              </div>
            )}

            <div style={{ fontSize: "0.85rem", marginBottom: "0.75rem", lineHeight: 1.5 }}>
              <span style={{ color: "var(--text-muted)" }}>Rationale:</span> {p.rationale}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Proposed {new Date(p.created_at).toLocaleString()} by {p.source}
                {p.decided_at && ` · Decided ${new Date(p.decided_at).toLocaleString()}`}
                {p.rejection_reason && ` · Reason: ${p.rejection_reason}`}
              </div>

              {p.status === "pending" && (
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    onClick={() => handleApprove(p.id, p.ticker)}
                    disabled={actionLoading === p.id}
                    style={{
                      padding: "0.4rem 1rem", border: "none", borderRadius: "4px",
                      background: "var(--green)", color: "#fff", cursor: "pointer",
                      fontSize: "0.85rem", fontWeight: 600, opacity: actionLoading === p.id ? 0.5 : 1,
                    }}
                  >
                    {actionLoading === p.id ? "..." : "Approve"}
                  </button>
                  <button
                    onClick={() => handleReject(p.id, p.ticker)}
                    disabled={actionLoading === p.id}
                    style={{
                      padding: "0.4rem 1rem", border: "1px solid var(--red)", borderRadius: "4px",
                      background: "transparent", color: "var(--red)", cursor: "pointer",
                      fontSize: "0.85rem", fontWeight: 600, opacity: actionLoading === p.id ? 0.5 : 1,
                    }}
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
