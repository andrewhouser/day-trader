"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";

export default function Sentiment() {
  const [entries, setEntries] = useState<{ raw: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSentiment(20).then(setEntries).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading sentiment...</div>;
  if (entries.length === 0) return <div className="empty-state">No sentiment analysis yet. The agent scores news headlines 3x daily.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingBottom: "2rem" }}>
      <div className="section-title">Sentiment Analysis ({entries.length})</div>
      {entries.map((entry, i) => (
        <div key={i} className="card markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.raw}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}
