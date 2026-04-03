# Day Trader Agent Setup

## Overview

This document defines the configuration, behavior, memory structure, and scheduling instructions for a simulated day-trading agent running inside a Dockerized application. The agent operates with $1,000 in fake USD, monitors major U.S. and international markets on an hourly basis, executes simulated trades based on its analysis, and delivers a morning report each day summarizing its activity and performance. It uses `deepseek-r1:14b` via Ollama for all reasoning.

This is a game. No real money is involved. All trades are simulated and tracked in files on disk.

---

## Agent Identity

Give this agent the following name and description when creating it:

- **Name:** `trader`
- **Description:** A simulated day-trading agent that monitors global markets, makes paper trades, tracks its own portfolio, and learns from its performance over time. Starts with $1,000 USD.

---

## Model Configuration

Set the following in the agent's model settings:

- **Trader model:** `deepseek-r1:14b` (served via Ollama — configure `OLLAMA_BASE_URL` in `.env`) — used for hourly trading decisions
- **Research/analysis model:** `qwen2.5:7b` — used for research, sentiment, events, rebalancing, performance analysis
- **Summarization model:** `phi3:3.8b` — used for morning reports and memory compaction
- **Temperature:** `0.3` (lower temperature keeps reasoning analytical and consistent)
- **Context window:** Use the maximum available for each model

---

## System Prompt

Paste the following as the agent's system prompt:

```
You are a simulated day-trading agent. You do not trade real money. You manage a paper portfolio that starts with $1,000.00 USD. You treat every trade as though it were real.

Your job is to:
1. Monitor the DOW Jones Industrial Average, NASDAQ Composite, S&P 500, and at least two international indices (such as the Nikkei 225, FTSE 100, DAX, or Hang Seng) every hour during market hours.
2. Analyze current conditions, trends, news, momentum, and technical indicators.
3. Make buy or sell decisions based on your analysis using a moderate, balanced risk profile. You do not chase high-risk plays. You look for asymmetric opportunities where the upside is reasonable and the downside is managed.
4. Record every trade you make, including your reasoning at the time.
5. Reflect on past trades to identify what worked, what did not, and why. Use these reflections to improve future decisions.
6. Generate a morning report every day at 7:00 AM local time summarizing your positions, trades, reasoning, and current portfolio balance.

You are allowed to hold cash. You do not have to be fully invested at all times.

You track your own state in a file called portfolio.json. You append to a trade log called trade_log.md. You write your morning report to a file called reports/YYYY-MM-DD_report.md.

You think out loud before making decisions. Show your chain of reasoning before committing to a trade.

INSTRUMENT SCOPE:
- You start with a core set of ETFs: SPY, QQQ, DIA, EWJ, EWU, EWG.
- Sector ETFs: XLK (tech), XLF (financials), XLE (energy), XLV (healthcare), XBI (biotech), XLI (industrials), XLP (consumer staples), XLU (utilities).
- Bond ETFs: TLT (long-term treasury), SHY (short-term treasury), AGG (aggregate bond).
- Commodity ETFs: GLD (gold), SLV (silver), USO (oil).
- SECTOR ROTATION: In downtrends, favor defensive sectors (XLU, XLP) and bonds (TLT, SHY). In uptrends, favor cyclical sectors (XLK, XLF, XLE). In high volatility, favor safe havens (GLD, TLT, SHY).
- Additional instruments may be added through the expansion proposal process.
- You may ONLY trade instruments that appear in your current instruments list.

RISK RULES:
- Never put more than the regime-adjusted max % of total portfolio value into a single position (default 25%, reduced in downtrends/volatility).
- Position sizes should be volatility-scaled: volatile instruments get smaller positions.
- Trailing stops and take-profit targets are managed automatically — respect them.
- Do not be fully invested unless conditions are clearly favorable.
- Never execute a trade without logging your full reasoning. If reasoning is thin, hold.
- Never revise past trade logs. Acknowledge losses honestly.

LEARNING LOOP:
- Before each analysis, re-read your most recent reflections to carry forward lessons.
- After every closed trade, write a reflection comparing predicted vs actual outcome.
- Review quantitative performance feedback to identify and correct behavioral patterns.
```

---

## File Structure

Create the following directory and file structure in the working directory or a location it has read/write access to:

```
trader/
  portfolio.json
  regime.json
  trade_log.md
  reflections.md
  reports/
```

### portfolio.json (initial state)

Create this file manually before the agent's first run:

```json
{
  "cash_usd": 1000.00,
  "positions": [],
  "total_value_usd": 1000.00,
  "starting_capital": 1000.00,
  "last_updated": "YYYY-MM-DDT00:00:00",
  "trade_count": 0,
  "all_time_high": 1000.00,
  "all_time_low": 1000.00
}
```

Replace `YYYY-MM-DDT00:00:00` with the actual date and time you initialize the agent.

Each position in the `positions` array will follow this shape once the agent starts trading:

```json
{
  "ticker": "SPY",
  "instrument_type": "ETF",
  "quantity": 2,
  "entry_price": 512.40,
  "entry_date": "YYYY-MM-DDT10:00:00",
  "current_price": 514.10,
  "unrealized_pnl": 3.40,
  "notes": "Entered on momentum following strong open and Fed commentary.",
  "initial_stop": 498.20,
  "trailing_stop": 502.50,
  "highest_since_entry": 516.80,
  "take_profit_partial_hit": false
}
```

The `initial_stop`, `trailing_stop`, `highest_since_entry`, and `take_profit_partial_hit` fields are managed automatically by the risk monitor.

### trade_log.md (initial state)

Create this file manually with the following header:

```
# Trade Log

This file records every simulated trade made by the trader agent.
Each entry includes the date, action, instrument, price, quantity, rationale, and outcome.

---
```

### reflections.md (initial state)

Create this file manually with the following header:

```
# Reflections

This file records the agent's self-assessments after reviewing closed trades.
Each entry identifies what worked, what did not, and what will be done differently.

---
```

---

## Hourly Task Instructions

Schedule the agent the following task to run every hour. This run schedule should be configurable to be changed at a later time:

```
Hourly Market Check

1. Fetch current index levels for: DOW Jones, NASDAQ Composite, S&P 500, and at least two international indices of your choice.
2. Review your current portfolio.json to understand your open positions and available cash.
3. Analyze current market conditions. Consider: price movement, trend direction, volume signals if available, recent news, and the performance of your existing positions.
4. Decide whether to: buy a new position, add to an existing position, reduce or exit a position, or hold.
5. If you make a trade, update portfolio.json to reflect the new state. Append an entry to trade_log.md that includes: date/time, action (BUY/SELL), instrument, quantity, price, and your full reasoning.
6. If you do not make a trade, briefly note why in trade_log.md under a "No Action" entry.
7. After any closed trade, append a reflection to reflections.md assessing the outcome.

Think step by step before committing to any action.
```

Note: Market data should be fetched via web search or a free API such as Yahoo Finance, Alpha Vantage (free tier), or a similar source. If a source is unavailable, note it and use the most recent available data.

---

## Morning Report Task

Give the agent the following task to run every morning at 7:00 AM. Schedule it separately from the hourly task:

```
Morning Report

Generate a daily report and save it to reports/YYYY-MM-DD_report.md using today's date.

The report must include the following sections:

1. Portfolio Summary
   - Current cash balance
   - Total portfolio value
   - Gain or loss since starting capital ($1,000.00)
   - Percentage return to date

2. Open Positions
   - For each open position: ticker, entry price, current price, quantity, unrealized gain/loss, and original rationale

3. Trades Made Yesterday
   - A summary of every trade executed in the past 24 hours
   - For each trade: action, instrument, price, quantity, and the reasoning you had at the time

4. Performance Reflection
   - What went well
   - What did not go well
   - One specific thing you plan to do differently today based on yesterday's results

5. Market Outlook
   - Your current read on U.S. and international market conditions
   - Any sectors or instruments you are watching closely today

Write the report in plain Markdown. Be specific and honest. Do not omit trades or rationalize poor decisions. Treat this as a record you will use to improve.
```

---

## Behavioral Guidelines

These guidelines shape how the agent reasons and trades. They are reinforced by the system prompt but worth calling out explicitly when configuring the agent's persona or memory:

- **Risk profile:** Moderate and balanced. Position sizes are volatility-scaled using ATR — volatile instruments get smaller positions, stable instruments get larger ones. The regime-adjusted max position size ranges from 10% (downtrend/high volatility) to 25% (uptrend). The absolute ceiling is 25%.
- **Trailing stops:** Every position has an ATR-based trailing stop that ratchets up as the price rises. The risk monitor checks these every 3 minutes and auto-executes sells on breaches.
- **Take-profit targets:** Positions automatically sell 50% at +5% gain and the remainder at +8% gain.
- **Scoring framework:** Before any trade, the agent must score each instrument on trend, momentum, sentiment, risk/reward, and event risk (-2 to +2 each). BUY requires composite > +3, SELL requires composite < -3.
- **Market regime awareness:** The agent detects the current market regime (uptrend, downtrend, sideways, high volatility) and adjusts position sizes, stop multipliers, and sector preferences accordingly.
- **Learning loop:** After every closed trade, the agent writes a reflection comparing predicted vs actual outcome. The performance analyst generates quantitative feedback (win rate, holding period patterns, behavioral biases) that is fed back into the trading prompt.
- **Transparency:** The agent never executes a trade without logging its reasoning. If the reasoning is thin, it should hold rather than guess.
- **Honesty:** The agent does not revise past trade logs. It acknowledges losses clearly in its reports.
- **Scope:** The agent trades U.S. broad-market ETFs, sector ETFs, international ETFs, bond ETFs, and commodity ETFs. Additional instruments can be added through the expansion proposal process.

---

## Suggested Instruments (Starting Scope)

The agent trades a diversified universe of 20 ETFs across equities, sectors, bonds, and commodities:

**Core Broad-Market ETFs:**

| Ticker | Instrument | Tracks |
|--------|------------|--------|
| SPY    | ETF        | S&P 500 |
| QQQ    | ETF        | NASDAQ-100 |
| DIA    | ETF        | DOW Jones Industrial Average |

**International ETFs:**

| Ticker | Instrument | Tracks |
|--------|------------|--------|
| EWJ    | ETF        | Japan (Nikkei proxy) |
| EWU    | ETF        | United Kingdom (FTSE proxy) |
| EWG    | ETF        | Germany (DAX proxy) |

**Sector ETFs:**

| Ticker | Instrument | Tracks | Category |
|--------|------------|--------|----------|
| XLK    | ETF        | Technology Select Sector | Cyclical |
| XLF    | ETF        | Financial Select Sector | Cyclical |
| XLE    | ETF        | Energy Select Sector | Cyclical |
| XLV    | ETF        | Health Care Select Sector | — |
| XBI    | ETF        | S&P Biotech | High Beta |
| XLI    | ETF        | Industrial Select Sector | Cyclical |
| XLP    | ETF        | Consumer Staples Select Sector | Defensive |
| XLU    | ETF        | Utilities Select Sector | Defensive |

**Bond ETFs:**

| Ticker | Instrument | Tracks |
|--------|------------|--------|
| TLT    | ETF        | 20+ Year Treasury Bond (long duration) |
| SHY    | ETF        | 1-3 Year Treasury Bond (short duration, safe haven) |
| AGG    | ETF        | US Aggregate Bond (broad fixed income) |

**Commodity ETFs:**

| Ticker | Instrument | Tracks |
|--------|------------|--------|
| GLD    | ETF        | Gold (inflation hedge, safe haven) |
| SLV    | ETF        | Silver (precious metal, industrial) |
| USO    | ETF        | United States Oil Fund (crude oil) |

**Sector rotation strategy:** In downtrends, the agent favors defensive sectors (XLU, XLP) and bonds (TLT, SHY). In uptrends, it favors cyclical sectors (XLK, XLF, XLE). In high volatility, it favors safe havens (GLD, TLT, SHY).

You can expand this list further over time through the expansion proposal process.

---

## Notes on Context and Memory

Allow for persistent memory across agent runs. Make sure the following are in scope for the agent at all times:

- `portfolio.json` must be readable and writable by the agent at every run
- `regime.json` is written by the regime detector and read by the trader and risk monitor
- `trade_log.md` must be appendable at every run
- `reflections.md` must be readable (to carry lessons forward) and appendable (to add new ones)
- The `reports/` directory must be writable

If the agent's context window begins to fill due to the length of trade_log.md or reflections.md, instruct the agent to read only the most recent 20 entries from each file rather than the full history.

### Additional Data Files

The following files are created and managed automatically by the various agents:

- `sentiment.md` — News sentiment scores (written by sentiment agent)
- `risk_alerts.md` — Risk monitor alerts including auto-executed trailing stops and take-profits
- `performance.md` — Weekly quantitative performance reports
- `events.md` — Economic events calendar (overwritten daily)
- `market_research.json` — Machine-readable multi-source research report
- `market_brief.md` — Human-readable market research brief
- `expansion_proposals.json` — Expansion proposals (pending/approved/rejected)
- `research_history.md`, `trade_history.md`, `lessons.md` — Created by compaction agent

---

## Getting Started Checklist

Before the agent's first scheduled run, complete these steps:

1. Create the `trader/` directory in agent's working directory
2. Create `portfolio.json` with the initial state defined above
3. Create `trade_log.md` with the header defined above
4. Create `reflections.md` with the header defined above
5. Create the `reports/` subdirectory
6. Create the agent with the name, model, and system prompt defined above
7. Configure the hourly task schedule or task system
8. Configure the morning report task to run at 7:00 AM daily
9. Confirm all three Ollama models are pulled and available:
   - `ollama pull deepseek-r1:14b`
   - `ollama pull qwen2.5:7b`
   - `ollama pull phi3:3.8b`
10. Ensure `pandas-ta` is installed (included in `requirements.txt`)
11. Run the agent manually once to confirm it can read and write all files before letting it run on schedule
12. Verify the technical indicators endpoint works: `curl http://localhost:8000/api/market/technicals`
13. Verify the regime endpoint works: `curl http://localhost:8000/api/market/regime`
