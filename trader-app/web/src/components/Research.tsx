"use client";

import { useEffect, useState } from "react";

import ReactMarkdown from "react-markdown";

import remarkGfm from "remark-gfm";

import { api } from "@/lib/api";

import styles from "./Research.module.css";

export function Research() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getResearch(30).then(setEntries).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading research...
      </div>
    );
  }
  if (entries.length === 0) {
    return (
      <div className="empty-state">
        No research notes yet. The agent generates these before each trading cycle.
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className="section-title">Research Notes ({entries.length})</div>
      {entries.map((entry, i) => (
        <div className="card markdown-body" key={i}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}
