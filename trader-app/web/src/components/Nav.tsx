"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Dashboard" },
  { href: "/trades", label: "Trades" },
  { href: "/technicals", label: "Technicals" },
  { href: "/research", label: "Research" },
  { href: "/expansion", label: "Expansion" },
  { href: "/sentiment", label: "Sentiment" },
  { href: "/risk", label: "Risk" },
  { href: "/events", label: "Events" },
  { href: "/performance", label: "Performance" },
  { href: "/reports", label: "Reports" },
  { href: "/reflections", label: "Reflections" },
  { href: "/tasks", label: "Tasks" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="nav" role="navigation" aria-label="Main navigation">
      {TABS.map((t) => (
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
    </nav>
  );
}
