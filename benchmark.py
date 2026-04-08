"""Portfolio-level benchmark comparison and parameter adaptation.

Compares portfolio performance against a buy-and-hold SPY benchmark over
the same time period, computes key portfolio-level metrics (Sharpe-like
ratio, cash drag, holding period efficiency), and produces concrete
parameter adjustment suggestions that are injected into the trading prompt.
"""
import json
import logging
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)

BENCHMARK_TICKER = "SPY"


def _load_portfolio_history() -> list[dict]:
    try:
        with open(config.PORTFOLIO_HISTORY_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _get_benchmark_return(start_date: datetime, end_date: datetime) -> float | None:
    """Compute SPY buy-and-hold return over the given period using yfinance."""
    try:
        import yfinance as yf

        # Pad dates slightly to ensure we get data
        start_str = (start_date - timedelta(days=3)).strftime("%Y-%m-%d")
        end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download(BENCHMARK_TICKER, start=start_str, end=end_str, progress=False)
        if df.empty or len(df) < 2:
            return None
        # Use first and last available close
        first_close = float(df["Close"].iloc[0])
        last_close = float(df["Close"].iloc[-1])
        if first_close <= 0:
            return None
        return round(((last_close - first_close) / first_close) * 100, 2)
    except Exception as e:
        logger.debug(f"Benchmark fetch failed: {e}")
        return None


def _compute_cash_drag(history: list[dict]) -> float | None:
    """Average percentage of portfolio held as cash across all snapshots."""
    if not history:
        return None
    cash_pcts = []
    for snap in history:
        total = snap.get("total_value_usd", 0)
        cash = snap.get("cash_usd", 0)
        if total > 0:
            cash_pcts.append((cash / total) * 100)
    return round(sum(cash_pcts) / len(cash_pcts), 1) if cash_pcts else None


def _compute_daily_returns(history: list[dict]) -> list[float]:
    """Extract daily returns from portfolio history (one per calendar day)."""
    if len(history) < 2:
        return []
    # Group by date, take last snapshot per day
    by_date: dict[str, float] = {}
    for snap in history:
        date_str = snap["timestamp"][:10]
        by_date[date_str] = snap["total_value_usd"]
    dates = sorted(by_date.keys())
    if len(dates) < 2:
        return []
    returns = []
    for i in range(1, len(dates)):
        prev = by_date[dates[i - 1]]
        curr = by_date[dates[i]]
        if prev > 0:
            returns.append((curr - prev) / prev)
    return returns


def _compute_sharpe_like(daily_returns: list[float]) -> float | None:
    """Annualized Sharpe-like ratio (assuming 0% risk-free rate)."""
    if len(daily_returns) < 5:
        return None
    import math

    mean_r = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
    std_r = math.sqrt(variance) if variance > 0 else 0
    if std_r == 0:
        return None
    # Annualize: 252 trading days
    return round((mean_r / std_r) * math.sqrt(252), 2)


def compute_benchmark_comparison() -> dict:
    """Compute portfolio vs benchmark metrics.

    Returns a dict with:
      - portfolio_return_pct
      - benchmark_return_pct (SPY buy-and-hold)
      - alpha (portfolio - benchmark)
      - avg_cash_pct (cash drag)
      - sharpe_like (annualized, 0% risk-free)
      - trading_days
      - suggestions: list of concrete parameter adjustment strings
    """
    from agent import load_portfolio

    portfolio = load_portfolio()
    history = _load_portfolio_history()

    result: dict = {
        "portfolio_return_pct": 0.0,
        "benchmark_return_pct": None,
        "alpha": None,
        "avg_cash_pct": None,
        "sharpe_like": None,
        "trading_days": 0,
        "suggestions": [],
    }

    if not history:
        return result

    # Portfolio return
    start_value = portfolio.get("starting_capital", 1000.0)
    current_value = portfolio.get("total_value_usd", start_value)
    port_return = round(((current_value - start_value) / start_value) * 100, 2)
    result["portfolio_return_pct"] = port_return

    # Time range
    first_ts = datetime.fromisoformat(history[0]["timestamp"])
    last_ts = datetime.fromisoformat(history[-1]["timestamp"])
    trading_days = max((last_ts - first_ts).days, 1)
    result["trading_days"] = trading_days

    # Benchmark
    bench_return = _get_benchmark_return(first_ts, last_ts)
    result["benchmark_return_pct"] = bench_return
    if bench_return is not None:
        result["alpha"] = round(port_return - bench_return, 2)

    # Cash drag
    avg_cash = _compute_cash_drag(history)
    result["avg_cash_pct"] = avg_cash

    # Sharpe-like
    daily_returns = _compute_daily_returns(history)
    result["sharpe_like"] = _compute_sharpe_like(daily_returns)

    # Generate concrete suggestions
    suggestions = _generate_suggestions(result, portfolio)
    result["suggestions"] = suggestions

    return result


def _generate_suggestions(metrics: dict, portfolio: dict) -> list[str]:
    """Generate concrete, actionable parameter suggestions based on metrics."""
    suggestions = []
    alpha = metrics.get("alpha")
    avg_cash = metrics.get("avg_cash_pct")
    port_return = metrics.get("portfolio_return_pct", 0)
    bench_return = metrics.get("benchmark_return_pct")
    trading_days = metrics.get("trading_days", 0)

    # Need at least 2 days of data to make meaningful suggestions
    if trading_days < 2:
        return ["Insufficient history — need at least 2 trading days for benchmark comparison."]

    # 1. Underperforming benchmark
    if alpha is not None and alpha < -1.0:
        suggestions.append(
            f"UNDERPERFORMING BENCHMARK: Portfolio {port_return:+.1f}% vs SPY {bench_return:+.1f}% "
            f"(alpha {alpha:+.1f}%). A simple buy-and-hold SPY would have done better. "
            f"Consider: are you trading too frequently, exiting winners too early, "
            f"or holding too much cash?"
        )

    # 2. Cash drag
    if avg_cash is not None and avg_cash > 60:
        suggestions.append(
            f"CASH DRAG: Average cash allocation is {avg_cash:.0f}%. "
            f"Uninvested cash earns nothing while the market moves. "
            f"Lower your buy threshold or increase position sizes to deploy capital."
        )
    elif avg_cash is not None and avg_cash > 40:
        suggestions.append(
            f"MODERATE CASH DRAG: Average cash allocation is {avg_cash:.0f}%. "
            f"Consider whether your buy threshold is too conservative."
        )

    # 3. Zero trades / no positions
    if portfolio.get("trade_count", 0) == 0 and trading_days >= 2:
        suggestions.append(
            "NO TRADES EXECUTED: The portfolio has been 100% cash since inception. "
            "The scoring thresholds or position limits may be too restrictive. "
            "Deploy capital — even a small position is better than missing the market entirely."
        )

    # 4. Positive alpha — reinforce
    if alpha is not None and alpha > 2.0:
        suggestions.append(
            f"OUTPERFORMING BENCHMARK: Portfolio {port_return:+.1f}% vs SPY {bench_return:+.1f}% "
            f"(alpha {alpha:+.1f}%). Current strategy is working — maintain approach."
        )

    # 5. Sharpe ratio feedback
    sharpe = metrics.get("sharpe_like")
    if sharpe is not None:
        if sharpe < 0:
            suggestions.append(
                f"NEGATIVE RISK-ADJUSTED RETURN: Sharpe-like ratio is {sharpe:.2f}. "
                f"Returns are negative relative to volatility. Reduce position sizes or "
                f"tighten stop-losses to limit downside."
            )
        elif sharpe < 0.5 and trading_days >= 5:
            suggestions.append(
                f"LOW RISK-ADJUSTED RETURN: Sharpe-like ratio is {sharpe:.2f}. "
                f"Consider whether the risk taken is justified by the returns."
            )

    return suggestions


def get_benchmark_for_prompt() -> str:
    """Generate benchmark comparison text for injection into the trading prompt."""
    try:
        metrics = compute_benchmark_comparison()
    except Exception as e:
        logger.debug(f"Benchmark comparison failed: {e}")
        return "Benchmark comparison unavailable."

    lines = ["### Portfolio vs Benchmark (SPY Buy-and-Hold)"]

    port_ret = metrics["portfolio_return_pct"]
    bench_ret = metrics["benchmark_return_pct"]
    alpha = metrics["alpha"]
    days = metrics["trading_days"]

    lines.append(f"- Portfolio return: {port_ret:+.2f}% over {days} day(s)")
    if bench_ret is not None:
        lines.append(f"- SPY buy-and-hold: {bench_ret:+.2f}% (same period)")
        emoji = "✅" if (alpha or 0) >= 0 else "❌"
        lines.append(f"- Alpha: {alpha:+.2f}% {emoji}")
    else:
        lines.append("- SPY benchmark: unavailable (data fetch failed)")

    avg_cash = metrics.get("avg_cash_pct")
    if avg_cash is not None:
        lines.append(f"- Average cash allocation: {avg_cash:.0f}%")

    sharpe = metrics.get("sharpe_like")
    if sharpe is not None:
        lines.append(f"- Sharpe-like ratio (annualized): {sharpe:.2f}")

    suggestions = metrics.get("suggestions", [])
    if suggestions:
        lines.append("")
        for s in suggestions:
            lines.append(f"⚡ {s}")

    return "\n".join(lines)
