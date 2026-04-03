"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface TabGroup {
  label: string;
  tabs: { href: string; label: string }[];
}

const TAB_GROUPS: TabGroup[] = [
  {
    label: "Overview",
    tabs: [{ href: "/", label: "Dashboard" }],
  },
  {
    label: "Trading",
    tabs: [
      { href: "/trades", label: "Trades" },
      { href: "/technicals", label: "Technicals" },
      { href: "/research", label: "Research" },
      { href: "/expansion", label: "Expansion" },
    ],
  },
  {
    label: "Analysis",
    tabs: [
      { href: "/sentiment", label: "Sentiment" },
      { href: "/risk", label: "Risk" },
      { href: "/events", label: "Events" },
      { href: "/performance", label: "Performance" },
    ],
  },
  {
    label: "History",
    tabs: [
      { href: "/reports", label: "Reports" },
      { href: "/reflections", label: "Reflections" },
    ],
  },
  {
    label: "System",
    tabs: [
      { href: "/tasks", label: "Tasks" },
      { href: "/chat", label: "Chat" },
    ],
  },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="nav" role="navigation" aria-label="Main navigation">
      {TAB_GROUPS.map((group) => (
        <div key={group.label} className="nav-group" role="tablist" aria-label={group.label}>
          <span className="nav-group-label">{group.label}</span>
          <div className="nav-group-tabs">
            {group.tabs.map((t) => (
              <Link
                key={t.href}
                href={t.href}
                className={pathname === t.href ? "active" : ""}
                role="tab"
                aria-selected={pathname === t.href}
              >
                {t.label}
              </Link>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
