"use client";

import { useEffect, useState } from "react";

import { api, NewsArticle } from "@/lib/api";

import styles from "./News.module.css";

function timeAgo(dateStr: string): string {
  if (!dateStr) return "";
  const diffMs = new Date().getTime() - new Date(dateStr).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function News() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getNews()
      .then((r) => setArticles(r.articles))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading news...
      </div>
    );
  }
  if (error) {
    return <div className={`card ${styles.errorCard}`}>Error: {error}</div>;
  }

  const allTickers = [...new Set(articles.flatMap((a) => a.tickers).filter(Boolean))].sort();
  const filtered = filter
    ? articles.filter(
        (a) =>
          a.tickers.some((t) => t.toUpperCase().includes(filter.toUpperCase())) ||
          a.related_query.toUpperCase().includes(filter.toUpperCase()) ||
          a.title.toLowerCase().includes(filter.toLowerCase())
      )
    : articles;

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div className={`section-title ${styles.sectionTitleInline}`}>
          Market News ({filtered.length})
        </div>
      </div>

      {allTickers.length > 0 && (
        <div className={styles.filterRow}>
          <button
            className={`badge ${!filter ? "badge-blue" : "badge-gray"}`}
            onClick={() => setFilter("")}
            style={{ border: "none", cursor: "pointer", fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
          >
            All
          </button>
          {allTickers.map((t) => (
            <button
              className={`badge ${filter === t ? "badge-blue" : "badge-gray"}`}
              key={t}
              onClick={() => setFilter(filter === t ? "" : t)}
              style={{ border: "none", cursor: "pointer", fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="empty-state">
          No news articles found{filter ? ` for "${filter}"` : ""}.
        </div>
      ) : (
        filtered.map((article, i) => (
          <a
            className={styles.articleCardLink}
            href={article.url}
            key={i}
            rel="noopener noreferrer"
            target="_blank"
          >
            <div className={`card ${styles.articleCard}`}>
              <div className={styles.articleHeader}>
                <div className={styles.articleContent}>
                  <div className={styles.articleTitle}>{article.title}</div>
                  <div className={styles.articleMeta}>
                    {article.source && <span>{article.source}</span>}
                    {article.published && <span>{timeAgo(article.published)}</span>}
                  </div>
                </div>
                {article.tickers.length > 0 && (
                  <div className={styles.tickerList}>
                    {article.tickers.slice(0, 5).map((t) => (
                      <span className={`badge badge-blue ${styles.tickerBadge}`} key={t}>
                        {t}
                      </span>
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
