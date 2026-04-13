"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

import { TickerChart } from "./TickerChart";

import styles from "./IndexTracker.module.css";

interface IndexData {
  change?: number;
  change_pct?: number;
  error?: string;
  price?: number;
  symbol: string;
}

export function IndexTracker() {
  const [indices, setIndices] = useState<Record<string, IndexData> | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<{ name: string; symbol: string } | null>(null);

  useEffect(() => {
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  function load() {
    api
      .getIndices()
      .then((d) => setIndices(d as Record<string, IndexData>))
      .catch(() => {});
  }

  if (!indices) return null;

  const entries = Object.entries(indices);
  if (entries.length === 0) return null;

  return (
    <>
      <div className={styles.indexTracker}>
        {entries.map(([name, data]) => {
          if (data.error) {
            return (
              <div className={styles.indexItem} key={name}>
                <span className={styles.indexName}>{name}</span>
                <span className={styles.indexMuted}>—</span>
              </div>
            );
          }
          const up = (data.change ?? 0) >= 0;
          return (
            <div
              className={`${styles.indexItem} ${styles.clickable}`}
              key={name}
              onClick={() => setSelectedIndex({ name, symbol: data.symbol })}
            >
              <span className={styles.indexName}>{name}</span>
              <span className={styles.indexPrice}>
                {data.price?.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
              <span className={up ? styles.indexUp : styles.indexDown}>
                {up ? "▲" : "▼"} {Math.abs(data.change ?? 0).toFixed(2)} (
                {up ? "+" : ""}
                {data.change_pct?.toFixed(2)}%)
              </span>
            </div>
          );
        })}
      </div>

      {selectedIndex && (
        <TickerChart
          onClose={() => setSelectedIndex(null)}
          ticker={selectedIndex.symbol}
          title={`${selectedIndex.name} (${selectedIndex.symbol})`}
        />
      )}
    </>
  );
}
