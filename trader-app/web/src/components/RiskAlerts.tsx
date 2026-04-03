"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ParsedAlert {
  title: string;
  timestamp: string;
  items: { ticker: string; range: string; high: string; low: string }[];
  otherLines: string[];
}

function parseAlert(raw: string): ParsedAlert {
  const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);
  const alert: ParsedAlert = { title: "", timestamp: "", items: [], otherLines: [] };

  for (const line of lines) {
    // Match header like "## Risk Alert - 2026-04-03 09:12:06" or bold variant
    const headerMatch = line.match(/^#+\s*\*{0,2}(.+?)\*{0,2}$/) || line.match(/^\*{2}(.+?)\*{2}$/);
    if (headerMatch && line.toLowerCase().includes("risk alert")) {
      const dateMatch = line.match(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/);
      alert.title = "Risk Alert";
      alert.timestamp = dateMatch ? dateMatch[1] : "";
      continue;
    }

    // Match volatility entries like "⚡ VOLATILITY: EWJ intraday range 2.51% (H: $85.84 L: $83.74)"
    const volMatch = line.match(
      /[⚡*]*\s*VOLATILITY:\s*(\w+)\s+intraday range\s+([\d.]+%)\s*\(H:\s*\$([\d.]+)\s+L:\s*\$([\d.]+)\)/g
    );
    if (volMatch) {
      // There may be multiple entries on one line separated by ⚡
      const entryRegex =
        /VOLATILITY:\s*(\w+)\s+intraday range\s+([\d.]+%)\s*\(H:\s*\$([\d.]+)\s+L:\s*\$([\d.]+)\)/g;
      let m;
      while ((m = entryRegex.exec(line)) !== null) {
        alert.items.push({ ticker: m[1], range: m[2], high: `$${m[3]}`, low: `$${m[4]}` });
      }
      continue;
    }

    // Fallback: any other content
    const cleaned = line.replace(/^[-*⚡]+\s*/, "");
    if (cleaned) alert.otherLines.push(cleaned);
  }

  return alert;
}

export default function RiskAlerts() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRiskAlerts(30).then(setEntries).finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading risk alerts...
      </div>
    );
  if (entries.length === 0)
    return (
      <div className="empty-state">
        No risk alerts. The monitor checks every 3 minutes during market hours.
      </div>
    );

  const parsed = entries.map((e) => parseAlert(e.raw));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingBottom: "2rem" }}>
      <div className="section-title">Risk Alerts ({entries.length})</div>
      {parsed.map((alert, i) => (
        <div key={i} className="card">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: alert.items.length > 0 || alert.otherLines.length > 0 ? "0.75rem" : 0,
            }}
          >
            <span style={{ fontWeight: 600 }}>{alert.title || "Risk Alert"}</span>
            {alert.timestamp && (
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{alert.timestamp}</span>
            )}
          </div>

          {alert.items.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Intraday Range</th>
                  <th>High</th>
                  <th>Low</th>
                </tr>
              </thead>
              <tbody>
                {alert.items.map((item, j) => (
                  <tr key={j}>
                    <td style={{ fontWeight: 600 }}>{item.ticker}</td>
                    <td>
                      <span
                        className={`badge ${
                          parseFloat(item.range) >= 5
                            ? "badge-red"
                            : parseFloat(item.range) >= 3
                              ? "badge-yellow"
                              : "badge-blue"
                        }`}
                      >
                        {item.range}
                      </span>
                    </td>
                    <td>{item.high}</td>
                    <td>{item.low}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {alert.otherLines.length > 0 && (
            <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              {alert.otherLines.map((line, k) => (
                <div key={k}>{line}</div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
