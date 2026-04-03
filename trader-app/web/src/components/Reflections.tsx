"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";

export default function Reflections() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReflections(50).then(setEntries).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading reflections...</div>;
  if (entries.length === 0) return <div className="empty-state">No reflections yet. The agent writes these after closing trades.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingBottom: "2rem" }}>
      <div className="section-title">Agent Reflections ({entries.length})</div>
      {entries.map((entry, i) => (
        <div key={i} className="card markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}
