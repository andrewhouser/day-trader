import type { Metadata } from "next";

import { IndexTracker } from "@/components/IndexTracker";
import { Nav } from "@/components/Nav";

import "./globals.css";
import styles from "./layout.module.css";

export const metadata: Metadata = {
  description: "Simulated day-trading agent dashboard",
  title: "Day Trader Agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className={styles.header}>
          <div className={`container ${styles.headerContent}`}>
            <div className={styles.headerLogo}>
              <span className={styles.headerLogoEmoji}>📈</span>
              <span className={styles.headerTitle}>Day Trader Agent</span>
              <span className={styles.headerSubtitle}>Paper Trading Simulation</span>
            </div>
          </div>
        </header>
        <div className="container">
          <Nav />
          <IndexTracker />
          {children}
        </div>
      </body>
    </html>
  );
}
