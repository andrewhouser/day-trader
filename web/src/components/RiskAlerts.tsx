"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

import styles from "./RiskAlerts.module.css";

interface ParsedAlert {
  items: { high: string; low: string; range: string; ticker: string }[];
  otherLines: string[];
  timestamp: string;
  title: string;
}

function parseAlert(raw: string): ParsedAlert {
  const lines = raw
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  const alert: ParsedAlert = { items: [], otherLines: [], timestamp: "", title: "" };

  for (const line of lines) {
    const headerMatch =
      line.match(/^#+\s*\*{0,2}(.+?)\*{0,2}$/) || line.match(/^\*{2}(.+?)\*{2}$/);
    if (headerMatch && line.toLowerCase().includes("risk alert")) {
      const dateMatch = line.match(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/);
      alert.timestamp = dateMatch ? dateMatch[1] : "";
      alert.title = "Risk Alert";
      continue;
    }

    const volMatch = line.match(
      /[⚡*]*\s*VOLATILITY:\s*(\w+)\s+intraday range\s+([\d.]+%)\s*\(H:\s*\$([\d.]+)\s+L:\s*\$([\d.]+)\)/g
    );
    if (volMatch) {
      const entryRegex =
        /VOLATILITY:\s*(\w+)\s+intraday range\s+([\d.]+%)\s*\(H:\s*\$([\d.]+)\s+L:\s*\$([\d.]+)\)/g;
      let m;
      while ((m = entryRegex.exec(line)) !== null) {
        alert.items.push({ high: `$${m[3]}`, low: `$${m[4]}`, range: m[2], ticker: m[1] });
      }
      continue;
    }

    const cleaned = line.replace(/^[-*⚡]+\s*/, "");
    if (cleaned) alert.otherLines.push(cleaned);
  }

  return alert;
}

export function RiskAlerts() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRiskAlerts(5).then(setEntries).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading risk alerts...
      </div>
    );
  }
  if (entries.length === 0) {
    return (
      <div className="empty-state">
        No risk alerts. The monitor checks every 3 minutes during market hours.
      </div>
    );
  }

  const parsed = entries.map((e) => parseAlert(e.raw));

  return (
    <div className={styles.container}>
      <div className="section-title">Risk Alerts ({entries.length})</div>
      {parsed.map((alert, i) => (
        <div className="card" key={i}>
          <div
            className={`${styles.alertHeader} ${alert.items.length > 0 || alert.otherLines.length > 0 ? styles.alertHeaderWithContent : ""}`}
          >
            <span className={styles.alertTitle}>{alert.title || "Risk Alert"}</span>
            {alert.timestamp && (
              <span className={styles.alertTimestamp}>{alert.timestamp}</span>
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
                    <td className={styles.tickerCell}>{item.ticker}</td>
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
            <div className={styles.otherLines}>
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
