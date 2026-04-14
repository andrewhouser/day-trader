"use client";

import { useEffect, useMemo, useState } from "react";

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

const STANDALONE_TABS: Tab[] = [
  { href: "/", label: "Dashboard" },
];

const TAB_GROUPS: TabGroup[] = [
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
      { href: "/tasks", label: "Tasks" },
      { href: "/settings", label: "Settings" },
      { href: "/chat", label: "Chat" },
      { href: "/learn", label: "Learn" },
    ],
  },
];

function findActiveGroup(pathname: string): string | null {
  for (const group of TAB_GROUPS) {
    for (const tab of group.tabs) {
      if (tab.href === pathname) return group.label;
    }
  }
  return null;
}

export function Nav() {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState(0);

  const activeGroupLabel = useMemo(() => findActiveGroup(pathname), [pathname]);

  const activeGroup = useMemo(
    () => TAB_GROUPS.find((g) => g.label === activeGroupLabel) ?? null,
    [activeGroupLabel],
  );

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
      <div className={styles.bar}>
        {/* Standalone tabs (no sub-menu) */}
        {STANDALONE_TABS.map((t) => (
          <Link
            aria-selected={pathname === t.href}
            className={
              pathname === t.href
                ? `${styles.tab} ${styles.tabActive}`
                : styles.tab
            }
            href={t.href}
            key={t.href}
            role="tab"
          >
            {t.label}
          </Link>
        ))}

        {/* Group tabs with inline sub-tabs */}
        {TAB_GROUPS.map((group) => {
          const isActive = group.label === activeGroupLabel;
          return (
            <div className={styles.groupWrapper} key={group.label}>
              <Link
                aria-selected={isActive}
                className={
                  isActive
                    ? `${styles.tab} ${styles.tabActive}`
                    : styles.tab
                }
                href={group.tabs[0].href}
                role="tab"
              >
                {group.label}
              </Link>

              {isActive && activeGroup && (
                <div className={styles.subtabs}>
                  {activeGroup.tabs.map((t) => (
                    <Link
                      aria-selected={pathname === t.href}
                      className={
                        pathname === t.href
                          ? `${styles.subtab} ${styles.subtabActive}`
                          : styles.subtab
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
              )}
            </div>
          );
        })}
      </div>
    </nav>
  );
}
