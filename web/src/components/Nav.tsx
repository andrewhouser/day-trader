"use client";

import { useEffect, useState } from "react";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/lib/api";

import styles from "./Nav.module.css";

interface Tab {
  href: string;
  label: string;
}

interface TabGroup {
  label: string;
  tabs: Tab[];
}

const TAB_GROUPS: TabGroup[] = [
  {
    label: "Overview",
    tabs: [
      { href: "/", label: "Dashboard" },
      { href: "/learn", label: "Learn" },
    ],
  },
  {
    label: "Trading",
    tabs: [
      { href: "/expansion", label: "Expansion" },
      { href: "/research", label: "Research" },
      { href: "/technicals", label: "Technicals" },
      { href: "/trades", label: "Trades" },
    ],
  },
  {
    label: "Analysis",
    tabs: [
      { href: "/events", label: "Events" },
      { href: "/news", label: "News" },
      { href: "/overseas", label: "Overseas" },
      { href: "/performance", label: "Performance" },
      { href: "/risk", label: "Risk" },
      { href: "/sentiment", label: "Sentiment" },
    ],
  },
  {
    label: "History",
    tabs: [
      { href: "/reflections", label: "Reflections" },
      { href: "/reports", label: "Reports" },
    ],
  },
  {
    label: "System",
    tabs: [
      { href: "/chat", label: "Chat" },
      { href: "/tasks", label: "Tasks" },
    ],
  },
];

export function Nav() {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    let mounted = true;
    async function check() {
      try {
        const p = await api.getProposals("pending");
        if (mounted) setPendingCount(p.length);
      } catch {
        /* ignore */
      }
    }
    check();
    const id = setInterval(check, 60_000);
    return () => {
      clearInterval(id);
      mounted = false;
    };
  }, []);

  return (
    <nav aria-label="Main navigation" className={styles.nav} role="navigation">
      {TAB_GROUPS.map((group) => (
        <div
          aria-label={group.label}
          className={styles.navGroup}
          key={group.label}
          role="tablist"
        >
          <span className={styles.navGroupLabel}>{group.label}</span>
          <div className={styles.navGroupTabs}>
            {group.tabs.map((t) => (
              <Link
                aria-selected={pathname === t.href}
                className={
                  pathname === t.href
                    ? `${styles.navLink} ${styles.navLinkActive}`
                    : styles.navLink
                }
                href={t.href}
                key={t.href}
                role="tab"
              >
                {t.label}
                {t.href === "/expansion" && pendingCount > 0 && (
                  <span
                    aria-label={`${pendingCount} pending proposals`}
                    className={styles.pendingDot}
                  />
                )}
              </Link>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
