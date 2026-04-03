"use client";

import { useEffect, useState } from "react";
import { api, NewsArticle } from "@/lib/api";

function timeAgo(dateStr: string): string {
  if (!dateStr) return "";
  const now = new Date();
  const pub = new Date(dateStr);
  const diffMs = now.getTime() - pub.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function News() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.getNews()
      .then((r) => setArticles(r.articles))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state"><span className="spinner" /> Loading news...</div>;
  if (error) return <div className="card" style={{ color: "var(--red)" }}>Error: {error}</div>;

  const filtered = filter
    ? articles.filter((a) =>
        a.tickers.some((t) => t.toUpperCase().includes(filter.toUpperCase())) ||
        a.related_query.toUpperCase().includes(filter.toUpperCase()) ||
        a.title.toLowerCase().includes(filter.toLowerCase())
      )
    : articles;

  // Collect all unique tickers for filter buttons
  const allTickers = [...new Set(articles.flatMap((a) => a.tickers).filter(Boolean))].sort();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingBottom: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div className="section-title" style={{ margin: 0 }}>Market News ({filtered.length})</div>
      </div>

      {/* Ticker filter */}
      {allTickers.length > 0 && (
        <div style={{ display: "flex", gap: "0.3rem", flexWrap: "wrap" }}>
          <button
            className={`badge ${!filter ? "badge-blue" : "badge-gray"}`}
            style={{ cursor: "pointer", border: "none", padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
            onClick={() => setFilter("")}
          >
            All
          </button>
          {allTickers.map((t) => (
            <button
              key={t}
              className={`badge ${filter === t ? "badge-blue" : "badge-gray"}`}
              style={{ cursor: "pointer", border: "none", padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
              onClick={() => setFilter(filter === t ? "" : t)}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="empty-state">No news articles found{filter ? ` for "${filter}"` : ""}.</div>
      ) : (
        filtered.map((article, i) => (
          <a
            key={i}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="card" style={{ transition: "background 0.15s", cursor: "pointer" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-card-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg-card)")}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem", lineHeight: 1.4, marginBottom: "0.35rem" }}>
                    {article.title}
                  </div>
                  <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {article.source && <span>{article.source}</span>}
                    {article.published && <span>{timeAgo(article.published)}</span>}
                  </div>
                </div>
                {article.tickers.length > 0 && (
                  <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap", flexShrink: 0 }}>
                    {article.tickers.slice(0, 5).map((t) => (
                      <span key={t} className="badge badge-blue" style={{ fontSize: "0.65rem" }}>{t}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </a>
        ))
      )}
    </div>
  );
}
