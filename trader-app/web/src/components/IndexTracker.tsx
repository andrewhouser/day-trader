"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface IndexData {
  symbol: string;
  price?: number;
  change?: number;
  change_pct?: number;
  error?: string;
}

export default function IndexTracker() {
  const [indices, setIndices] = useState<Record<string, IndexData> | null>(null);

  useEffect(() => {
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  function load() {
    api.getIndices().then((d) => setIndices(d as Record<string, IndexData>)).catch(() => {});
  }

  if (!indices) return null;

  const entries = Object.entries(indices);
  if (entries.length === 0) return null;

  return (
    <div className="index-tracker">
      {entries.map(([name, data]) => {
        if (data.error) {
          return (
            <div key={name} className="index-item">
              <span className="index-name">{name}</span>
              <span className="index-muted">—</span>
            </div>
          );
        }
        const up = (data.change ?? 0) >= 0;
        return (
          <div key={name} className="index-item">
            <span className="index-name">{name}</span>
            <span className="index-price">
              {data.price?.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </span>
            <span className={up ? "index-up" : "index-down"}>
              {up ? "▲" : "▼"}{" "}
              {Math.abs(data.change ?? 0).toFixed(2)}{" "}
              ({up ? "+" : ""}{data.change_pct?.toFixed(2)}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}
