import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Day Trader Agent",
  description: "Simulated day-trading agent dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--border)" }}>
          <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <span style={{ fontSize: "1.25rem" }}>📈</span>
              <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>Day Trader Agent</span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Paper Trading Simulation</span>
            </div>
          </div>
        </header>
        <div className="container">
          <Nav />
          {children}
        </div>
      </body>
    </html>
  );
}
