"use client";

import { StressScenario } from "@/lib/api";

import styles from "./ScenarioCard.module.css";

interface Props {
  currentValue: number;
  scenario: StressScenario;
}

export function ScenarioCard({ currentValue, scenario }: Props) {
  const isNegative = scenario.pct_change < 0;

  return (
    <div className="card">
      <div className={styles.header}>
        <div>
          <div className={styles.scenarioName}>{scenario.name}</div>
          <div className={styles.scenarioDescription}>{scenario.description}</div>
        </div>
        <span
          className={`badge ${isNegative ? "badge-red" : "badge-green"} ${styles.pctBadge}`}
        >
          {scenario.pct_change >= 0 ? "+" : ""}
          {scenario.pct_change}%
        </span>
      </div>

      <div className={styles.details}>
        <div>
          <span className={styles.currentLabel}>Current: </span>
          <span className={styles.statValue}>
            ${currentValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </span>
        </div>
        <div>
          <span className={styles.shockedLabel}>Shocked: </span>
          <span className={isNegative ? styles.shockedValueNegative : styles.shockedValuePositive}>
            ${scenario.shocked_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {scenario.positions_stopped_out.length > 0 && (
        <div className={styles.subsection}>
          <div className={styles.subsectionTitle}>Positions Stopped Out</div>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Stop Type</th>
                <th>Est. Loss</th>
              </tr>
            </thead>
            <tbody>
              {scenario.positions_stopped_out.map((p, i) => (
                <tr key={i}>
                  <td className={styles.tickerCell}>{p.ticker}</td>
                  <td>
                    <span className="badge badge-red">{p.stop_type.replace("_", " ")}</span>
                  </td>
                  <td className={styles.estimatedLoss}>${p.estimated_loss.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {scenario.positions_oversized && scenario.positions_oversized.length > 0 && (
        <div className={styles.subsection}>
          <div className={styles.subsectionTitle}>Oversized Positions</div>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Current %</th>
              </tr>
            </thead>
            <tbody>
              {scenario.positions_oversized.map((p, i) => (
                <tr key={i}>
                  <td className={styles.tickerCell}>{p.ticker}</td>
                  <td>
                    <span className="badge badge-yellow">{p.current_pct.toFixed(1)}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {scenario.forced_reduction_cost != null && (
            <div className={styles.reductionNote}>
              Estimated forced reduction: ${scenario.forced_reduction_cost.toFixed(2)}
            </div>
          )}
        </div>
      )}

      <div className={styles.summary}>{scenario.summary}</div>
    </div>
  );
}
