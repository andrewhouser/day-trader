"use client";

import styles from "./Technicals.module.css";

interface Props {
  label: string;
  tooltips: Record<string, string>;
}

export function Tip({ label, tooltips }: Props) {
  const tip = tooltips[label];
  if (!tip) return <>{label}</>;
  return (
    <span className={styles.tipWrapper}>
      {label}
      <span className={styles.tipBubble}>{tip}</span>
    </span>
  );
}
