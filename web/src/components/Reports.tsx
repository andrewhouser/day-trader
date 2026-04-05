"use client";

import { useEffect, useState } from "react";

import ReactMarkdown from "react-markdown";

import remarkGfm from "remark-gfm";

import { api, ReportSummary } from "@/lib/api";

import styles from "./Reports.module.css";

export function Reports() {
  const [contents, setContents] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [openFile, setOpenFile] = useState<string | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);

  useEffect(() => {
    api
      .getReports()
      .then((r) => {
        setReports(r);
        if (r.length > 0) loadAndOpen(r[0].filename);
      })
      .finally(() => setLoading(false));
  }, []);

  async function loadAndOpen(filename: string) {
    if (!contents[filename]) {
      const detail = await api.getReport(filename);
      setContents((prev) => ({ ...prev, [filename]: detail.content }));
    }
    setOpenFile((prev) => (prev === filename ? null : filename));
  }

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading reports...
      </div>
    );
  }
  if (reports.length === 0) {
    return <div className="empty-state">No morning reports generated yet.</div>;
  }

  return (
    <div className={styles.container}>
      <div className="section-title">Morning Reports ({reports.length})</div>
      {reports.map((r, i) => {
        const isOpen = openFile === r.filename;
        return (
          <div className="card" key={r.filename} style={{ overflow: "hidden", padding: 0 }}>
            <button
              aria-expanded={isOpen}
              className={styles.accordionTrigger}
              onClick={() => loadAndOpen(r.filename)}
            >
              <span
                className={`${styles.accordionChevron} ${isOpen ? styles.accordionChevronOpen : ""}`}
              >
                ▶
              </span>
              <span className={styles.accordionTitle}>{r.date}</span>
              {i === 0 && (
                <span className={`badge badge-blue ${styles.latestBadge}`}>Latest</span>
              )}
            </button>
            {isOpen && (
              <div className={`${styles.accordionContent} markdown-body`}>
                {contents[r.filename] ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{contents[r.filename]}</ReactMarkdown>
                ) : (
                  <div className="empty-state">
                    <span className="spinner" /> Loading...
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
