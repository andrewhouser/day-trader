"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";

export default function Events() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getEvents().then((data) => setContent(data.content)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading events...</div>;
  if (!content || content === "No events calendar generated yet.") {
    return <div className="empty-state">No events calendar yet. Updated daily at 6 AM.</div>;
  }

  return (
    <div style={{ paddingBottom: "2rem" }}>
      <div className="section-title">Economic Events Calendar</div>
      <div className="card markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
