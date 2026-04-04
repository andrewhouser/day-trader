"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { api } from "@/lib/api";

import styles from "./Reflections.module.css";

export function Reflections() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReflections(50).then(setEntries).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading reflections...
      </div>
    );
  }
  if (entries.length === 0) {
    return (
      <div className="empty-state">
        No reflections yet. The agent writes these after closing trades.
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className="section-title">Agent Reflections ({entries.length})</div>
      {entries.map((entry, i) => (
        <div className="card markdown-body" key={i}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}
