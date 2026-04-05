import styles from "./Learn.module.css";

export function Learn() {
  return (
    <div className={styles.container}>
      {/* Hero */}
      <div className={styles.hero}>
        <div className={styles.heroTitle}>How This Trading System Works</div>
        <div className={styles.heroSub}>
          This is a paper trading simulator — no real money is involved. An AI agent
          manages a simulated $1,000 portfolio, making buy and sell decisions based on
          market data, technical analysis, news sentiment, and its own learning from
          past trades. This page explains the investing concepts behind each part of
          the system and how the different agents work together.
        </div>
      </div>

      {/* Core Concepts */}
      <div className={styles.sectionTitle}>
        <span className={styles.sectionIcon}>📚</span> Core Investing Concepts
      </div>
      <div className={styles.conceptGrid}>
        <div className={styles.conceptCard}>
          <div className={styles.conceptName}>Portfolio &amp; Positions</div>
          <div className={styles.conceptBody}>
            A portfolio is the collection of investments you own. Each individual
            investment is called a position. When you buy shares of an ETF like SPY,
            that becomes a position in your portfolio. The goal is to grow the total
            value over time while managing risk.
          </div>
        </div>
        <div className={styles.conceptCard}>
          <div className={styles.conceptName}>ETFs (Exchange-Traded Funds)</div>
          <div className={styles.conceptBody}>
            An ETF is a basket of stocks or bonds bundled into a single tradeable
            instrument. Instead of buying 500 individual stocks, you can buy SPY
            (which tracks the S&amp;P 500) and get exposure to all of them at once.
            This system primarily trades ETFs for diversification and simplicity.
          </div>
        </div>
        <div className={styles.conceptCard}>
          <div className={styles.conceptName}>Bull vs. Bear Markets</div>
          <div className={styles.conceptBody}>
            A bull market means prices are generally rising — investors are optimistic.
            A bear market means prices are falling — investors are fearful. The system
            detects the current &quot;regime&quot; (uptrend, downtrend, sideways, high volatility)
            and adjusts its strategy accordingly — for example, favoring defensive
            investments during downtrends.
          </div>
        </div>
        <div className={styles.conceptCard}>
          <div className={styles.conceptName}>Risk Management</div>
          <div className={styles.conceptBody}>
            The most important rule in investing: don&apos;t lose more than you can afford.
            Risk management includes setting stop-losses (automatic sell points if a
            position drops too far), limiting how much goes into any single investment,
            and keeping some cash available for opportunities.
          </div>
        </div>
        <div className={styles.conceptCard}>
          <div className={styles.conceptName}>Technical Analysis</div>
          <div className={styles.conceptBody}>
            Technical analysis uses price and volume data to identify patterns and
            trends. Moving averages smooth out noise to show direction. RSI measures
            if something is overbought or oversold. MACD detects momentum shifts.
            These aren&apos;t crystal balls — they&apos;re statistical tools that improve the
            odds of making good decisions.
          </div>
        </div>
        <div className={styles.conceptCard}>
          <div className={styles.conceptName}>Diversification</div>
          <div className={styles.conceptBody}>
            &quot;Don&apos;t put all your eggs in one basket.&quot; Diversification means spreading
            investments across different asset types (stocks, bonds, commodities),
            sectors (tech, healthcare, energy), and geographies (U.S., Europe, Asia).
            When one area drops, others may hold steady or rise, reducing overall risk.
          </div>
        </div>
      </div>

      {/* Daily Flow */}
      <div className={styles.sectionTitle}>
        <span className={styles.sectionIcon}>🔄</span> The Daily Trading Cycle
      </div>
      <div className={styles.flowContainer}>
        <div className={styles.flowStep}>
          <div className={styles.flowNumber}>1</div>
          <div className={styles.flowContent}>
            <div className={styles.flowLabel}>Asia Markets Open (Overnight)</div>
            <div className={styles.flowDesc}>
              The Nikkei monitor tracks the Tokyo Stock Exchange during its morning
              and afternoon sessions. It watches for significant moves in Japanese
              equities, yen dynamics, and BOJ policy signals that could affect U.S.
              markets the next day. If a big move is detected, it emits a trade signal.
            </div>
            <div className={styles.flowTime}>~7:30 PM – 2:30 AM ET</div>
          </div>
        </div>
        <div className={styles.flowStep}>
          <div className={styles.flowNumber}>2</div>
          <div className={styles.flowContent}>
            <div className={styles.flowLabel}>Europe Markets Open (Early Morning)</div>
            <div className={styles.flowDesc}>
              The FTSE monitor picks up where Asia left off, tracking the London Stock
              Exchange and European markets. It reads the Asia summary for continuity
              and watches for sector rotation, currency moves, and ECB/BOE policy signals.
            </div>
            <div className={styles.flowTime}>~2:30 AM – 5:30 AM ET</div>
          </div>
        </div>
        <div className={styles.flowStep}>
          <div className={styles.flowNumber}>3</div>
          <div className={styles.flowContent}>
            <div className={styles.flowLabel}>Europe Handoff &amp; Pre-Market Prep</div>
            <div className={styles.flowDesc}>
              A handoff agent synthesizes all overnight data from Asia and Europe into
              a single briefing. The events agent checks for scheduled economic releases.
              The market context agent updates the rolling 30-day view. Memory compaction
              trims old data to keep the agent&apos;s context focused.
            </div>
            <div className={styles.flowTime}>5:00 AM – 7:00 AM ET</div>
          </div>
        </div>
        <div className={styles.flowStep}>
          <div className={styles.flowNumber}>4</div>
          <div className={styles.flowContent}>
            <div className={styles.flowLabel}>Morning Report</div>
            <div className={styles.flowDesc}>
              The agent produces a comprehensive daily report: portfolio status, overnight
              global recap, recent trade outcomes, and its outlook for the day. This is
              the agent&apos;s daily journal entry.
            </div>
            <div className={styles.flowTime}>7:00 AM ET</div>
          </div>
        </div>
        <div className={styles.flowStep}>
          <div className={styles.flowNumber}>5</div>
          <div className={styles.flowContent}>
            <div className={styles.flowLabel}>Market Hours — Research &amp; Trading</div>
            <div className={styles.flowDesc}>
              During U.S. market hours, the research agent gathers data from multiple
              sources every 10 minutes. The trading agent runs every 30 minutes, scoring
              each instrument on trend, momentum, sentiment, risk/reward, and sector
              divergence. It only trades when the composite score passes its threshold —
              no impulsive decisions. The risk monitor checks positions every 3 minutes.
            </div>
            <div className={styles.flowTime}>9:30 AM – 4:00 PM ET</div>
          </div>
        </div>
        <div className={styles.flowStep}>
          <div className={styles.flowNumber}>6</div>
          <div className={styles.flowContent}>
            <div className={styles.flowLabel}>Reflection &amp; Learning</div>
            <div className={styles.flowDesc}>
              After every closed trade, the agent writes a reflection evaluating whether
              its hypothesis was correct. Weekly performance analysis identifies patterns
              in wins and losses. The strategy playbook captures what works and suspends
              strategies that don&apos;t. This feedback loop is how the agent improves.
            </div>
            <div className={styles.flowTime}>Ongoing / Weekly</div>
          </div>
        </div>
      </div>

      {/* Agent Roles */}
      <div className={styles.sectionTitle}>
        <span className={styles.sectionIcon}>🤖</span> The Agent Team
      </div>
      <div className={styles.agentGrid}>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>🧠 Trading Agent</div>
          <div className={styles.agentRole}>
            The decision-maker. Analyzes all available data, scores instruments on
            multiple dimensions, and executes buy/sell trades when the evidence is
            strong enough. Uses the deepest reasoning model.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>🔬 Research Agent</div>
          <div className={styles.agentRole}>
            Gathers data from FRED, Finnhub, SEC filings, and financial news. Produces
            structured research notes identifying narratives, risks, and opportunities.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>🌏 Overseas Monitors</div>
          <div className={styles.agentRole}>
            Track Asia (Nikkei) and Europe (FTSE) markets overnight. Emit trade signals
            when significant moves are detected in international ETFs.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>📊 Sentiment Agent</div>
          <div className={styles.agentRole}>
            Reads news headlines and classifies the overall market mood as bullish,
            bearish, or neutral. Provides a qualitative signal alongside the numbers.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>⚠️ Risk Monitor</div>
          <div className={styles.agentRole}>
            Watches positions every 3 minutes for stop-loss breaches, volatility spikes,
            and concentration risk. The portfolio&apos;s safety net.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>⚖️ Rebalancer</div>
          <div className={styles.agentRole}>
            Weekly check on whether the portfolio has drifted from its target allocation.
            Suggests trades to restore balance between asset classes.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>📈 Performance Analyst</div>
          <div className={styles.agentRole}>
            Weekly deep-dive into trade outcomes, win rates, and patterns. Identifies
            what&apos;s working and what isn&apos;t, feeding lessons back to the trading agent.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>📋 Strategy Playbook</div>
          <div className={styles.agentRole}>
            Extracts recurring patterns from trade history with empirical win rates.
            High-confidence patterns get more weight; failing strategies get suspended.
          </div>
        </div>
        <div className={styles.agentCard}>
          <div className={styles.agentName}>🔍 Expansion Agent</div>
          <div className={styles.agentRole}>
            Periodically suggests new instruments for diversification. Proposals require
            your approval — this is your control over what the agent can trade.
          </div>
        </div>
      </div>

      {/* Glossary */}
      <div className={styles.sectionTitle}>
        <span className={styles.sectionIcon}>📖</span> Glossary
      </div>
      <div className={styles.glossaryGrid}>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>ATR (Average True Range)</div>
          <div className={styles.glossaryDef}>
            Measures how much an instrument&apos;s price typically moves in a day. Used to
            set stop-losses and size positions — volatile instruments get smaller positions.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>Bollinger Bands</div>
          <div className={styles.glossaryDef}>
            A channel around the moving average that widens when volatility increases.
            Prices near the upper band may be overextended; near the lower band may be
            oversold.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>Drawdown</div>
          <div className={styles.glossaryDef}>
            The decline from a portfolio&apos;s peak value to its lowest point. A 5% max
            drawdown means the portfolio never fell more than 5% from its highest value.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>MACD</div>
          <div className={styles.glossaryDef}>
            Moving Average Convergence Divergence — shows the relationship between two
            moving averages. When the MACD line crosses above the signal line, it suggests
            upward momentum.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>OBV (On-Balance Volume)</div>
          <div className={styles.glossaryDef}>
            Tracks whether volume is flowing into or out of an instrument. Rising OBV
            with rising price confirms the trend; divergence (price up, OBV down) warns
            of a potential reversal.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>Profit Factor</div>
          <div className={styles.glossaryDef}>
            Total gains divided by total losses. A profit factor above 1.0 means the
            system is profitable overall. Above 2.0 is considered strong.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>RSI (Relative Strength Index)</div>
          <div className={styles.glossaryDef}>
            Ranges from 0 to 100. Above 70 suggests overbought (may pull back); below
            30 suggests oversold (may bounce). The agent uses this as one input into its
            momentum score.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>SMA (Simple Moving Average)</div>
          <div className={styles.glossaryDef}>
            The average price over a set number of days (e.g., SMA-20 = 20-day average).
            When price is above the SMA, the trend is generally up. The agent checks
            alignment of SMA-20, SMA-50, and SMA-200.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>Stop-Loss</div>
          <div className={styles.glossaryDef}>
            A predetermined price at which a position is automatically sold to limit
            losses. A trailing stop moves up as the price rises, locking in gains while
            still protecting against reversals.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>VIX (Volatility Index)</div>
          <div className={styles.glossaryDef}>
            Often called the &quot;fear gauge.&quot; Measures expected market volatility over the
            next 30 days. A high VIX means investors expect big price swings. The agent
            reduces position sizes and favors safe havens when VIX is elevated.
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>Win Rate</div>
          <div className={styles.glossaryDef}>
            The percentage of closed trades that made money. A 60% win rate means 6 out
            of 10 trades were profitable. Win rate alone doesn&apos;t tell the full story —
            the size of wins vs. losses matters too (that&apos;s profit factor).
          </div>
        </div>
        <div className={styles.glossaryItem}>
          <div className={styles.glossaryTerm}>Market Regime</div>
          <div className={styles.glossaryDef}>
            The current state of the market: uptrend, downtrend, sideways, or high
            volatility. The agent adjusts its strategy for each regime — smaller positions
            in downtrends, wider stops in high volatility, more aggressive in uptrends.
          </div>
        </div>
      </div>
    </div>
  );
}
