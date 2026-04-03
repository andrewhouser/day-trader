"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, ReportSummary } from "@/lib/api";

export default function Reports() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [contents, setContents] = useState<Record<string, string>>({});
  const [openFile, setOpenFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReports().then((r) => {
      setReports(r);
      if (r.length > 0) loadAndOpen(r[0].filename);
    }).finally(() => setLoading(false));
  }, []);

  async function loadAndOpen(filename: string) {
    if (!contents[filename]) {
      const detail = await api.getReport(filename);
      setContents((prev) => ({ ...prev, [filename]: detail.content }));
    }
    setOpenFile((prev) => (prev === filename ? null : filename));
  }

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading reports...</div>;
  if (reports.length === 0) return <div className="empty-state">No morning reports generated yet.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", paddingBottom: "2rem" }}>
      <div className="section-title">Morning Reports ({reports.length})</div>
      {reports.map((r, i) => {
        const isOpen = openFile === r.filename;
        return (
          <div key={r.filename} className="card" style={{ padding: 0, overflow: "hidden" }}>
            <button
              onClick={() => loadAndOpen(r.filename)}
              aria-expanded={isOpen}
              className="accordion-trigger"
            >
              <span className="accordion-chevron" data-open={isOpen}>▶</span>
              <span className="accordion-title">{r.date}</span>
              {i === 0 && <span className="badge badge-blue" style={{ marginLeft: "auto" }}>Latest</span>}
            </button>
            {isOpen && (
              <div className="accordion-content markdown-body">
                {contents[r.filename] ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{contents[r.filename]}</ReactMarkdown>
                ) : (
                  <div className="empty-state"><span className="spinner" /> Loading...</div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
