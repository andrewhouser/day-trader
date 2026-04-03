"use client";

import { useEffect, useState } from "react";
import { api, StressTestResult, StressScenario } from "@/lib/api";

function ScenarioCard({ scenario, currentValue }: { scenario: StressScenario; currentValue: number }) {
  const isNegative = scenario.pct_change < 0;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
        <div>
          <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{scenario.name}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{scenario.description}</div>
        </div>
        <span className={`badge ${isNegative ? "badge-red" : "badge-green"}`} style={{ fontSize: "0.9rem", padding: "0.3rem 0.75rem" }}>
          {scenario.pct_change >= 0 ? "+" : ""}{scenario.pct_change}%
        </span>
      </div>

      <div style={{ display: "flex", gap: "1.5rem", marginBottom: "0.75rem", fontSize: "0.85rem" }}>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Current: </span>
          <span style={{ fontWeight: 600 }}>${currentValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Shocked: </span>
          <span style={{ fontWeight: 600, color: isNegative ? "var(--red)" : "var(--green)" }}>
            ${scenario.shocked_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {scenario.positions_stopped_out.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.35rem" }}>Positions Stopped Out</div>
          <table>
            <thead>
              <tr><th>Ticker</th><th>Stop Type</th><th>Est. Loss</th></tr>
            </thead>
            <tbody>
              {scenario.positions_stopped_out.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{p.ticker}</td>
                  <td><span className="badge badge-red">{p.stop_type.replace("_", " ")}</span></td>
                  <td style={{ color: "var(--red)" }}>${p.estimated_loss.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {scenario.positions_oversized && scenario.positions_oversized.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.35rem" }}>Oversized Positions</div>
          <table>
            <thead>
              <tr><th>Ticker</th><th>Current %</th></tr>
            </thead>
            <tbody>
              {scenario.positions_oversized.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{p.ticker}</td>
                  <td><span className="badge badge-yellow">{p.current_pct.toFixed(1)}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {scenario.forced_reduction_cost != null && (
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>
              Estimated forced reduction: ${scenario.forced_reduction_cost.toFixed(2)}
            </div>
          )}
        </div>
      )}

      <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontStyle: "italic" }}>
        {scenario.summary}
      </div>
    </div>
  );
}

export default function StressTest() {
  const [result, setResult] = useState<StressTestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    api.getStressTest()
      .then(setResult)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Running stress scenarios...</div>;
  if (error) return <div className="card" style={{ color: "var(--red)" }}>Error: {error}</div>;
  if (!result) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div className="section-title" style={{ margin: 0 }}>Portfolio Stress Scenarios</div>
        <button onClick={load} style={{ fontSize: "0.8rem" }}>Re-run</button>
      </div>
      {result.scenarios.map((s, i) => (
        <ScenarioCard key={i} scenario={s} currentValue={result.current_portfolio_value} />
      ))}
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textAlign: "center" }}>
        Cached for 5 minutes · Last run: {new Date(result.timestamp).toLocaleString()}
      </div>
    </div>
  );
}
