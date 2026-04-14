"""Market regime detection module.

Classifies the current market into one of:
STRONG_UPTREND, UPTREND, SIDEWAYS, DOWNTREND, STRONG_DOWNTREND, HIGH_VOLATILITY

Uses SPY technicals, VIX level, and rate of change as signals."""
import json
import logging
import os
from datetime import datetime

import config

logger = logging.getLogger(__name__)

REGIME_PATH = os.path.join(config.DATA_DIR, "regime.json")

# Regime classifications
STRONG_UPTREND = "STRONG_UPTREND"
UPTREND = "UPTREND"
SIDEWAYS = "SIDEWAYS"
DOWNTREND = "DOWNTREND"
STRONG_DOWNTREND = "STRONG_DOWNTREND"
HIGH_VOLATILITY = "HIGH_VOLATILITY"


def detect_regime(technicals: dict | None = None) -> dict:
    """Classify the current market regime based on SPY technicals and VIX.

    Args:
        technicals: Pre-fetched technical indicators dict. If None, fetches fresh.

    Returns:
        Dict with regime classification and supporting signals.
    """
    if technicals is None:
        from core.market_data import fetch_technical_indicators
        technicals = fetch_technical_indicators()

    spy_data = technicals.get("SPY", {})
    if "error" in spy_data or not spy_data:
        return _default_regime("No SPY data available")

    price = spy_data.get("price")
    sma50 = spy_data.get("sma_50")
    sma200 = spy_data.get("sma_200")
    rsi = spy_data.get("rsi_14")
    roc_20 = spy_data.get("roc_20")
    atr = spy_data.get("atr_14")

    if any(v is None for v in [price, sma50, sma200, rsi]):
        return _default_regime("Insufficient indicator data")

    # Signals
    above_sma50 = price > sma50
    above_sma200 = price > sma200
    golden_cross = sma50 > sma200  # SMA 50 above SMA 200
    rsi_level = rsi

    # Try to get VIX level from FRED research data or yfinance
    vix_level = _get_vix_level()

    # Rate of change
    roc = roc_20 if roc_20 is not None else 0

    # Classify regime
    regime = _classify(
        above_sma50=above_sma50,
        above_sma200=above_sma200,
        golden_cross=golden_cross,
        rsi=rsi_level,
        vix=vix_level,
        roc=roc,
    )

    result = {
        "regime": regime,
        "timestamp": datetime.now().isoformat(),
        "signals": {
            "spy_price": price,
            "sma_50": sma50,
            "sma_200": sma200,
            "above_sma50": above_sma50,
            "above_sma200": above_sma200,
            "golden_cross": golden_cross,
            "rsi": rsi_level,
            "vix": vix_level,
            "roc_20": roc,
        },
        "parameters": config.REGIME_PARAMS.get(regime, config.REGIME_PARAMS[SIDEWAYS]),
    }

    # Save to disk
    try:
        with open(REGIME_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save regime data: {e}")

    logger.info(f"Market regime: {regime} (RSI={rsi_level}, VIX={vix_level}, ROC={roc})")
    return result


def _classify(above_sma50: bool, above_sma200: bool, golden_cross: bool,
              rsi: float, vix: float | None, roc: float) -> str:
    """Classify regime from signals."""
    # HIGH_VOLATILITY takes priority if VIX is extreme
    if vix is not None and vix > 30:
        return HIGH_VOLATILITY

    # Strong uptrend: above both SMAs, golden cross, strong momentum
    if above_sma50 and above_sma200 and golden_cross and roc > 3:
        return STRONG_UPTREND

    # Uptrend: above both SMAs or golden cross with positive momentum
    if above_sma50 and above_sma200 and roc > 0:
        return UPTREND

    # Strong downtrend: below both SMAs, death cross, negative momentum
    if not above_sma50 and not above_sma200 and not golden_cross and roc < -3:
        return STRONG_DOWNTREND

    # Downtrend: below both SMAs or death cross
    if not above_sma50 and not above_sma200 and roc < 0:
        return DOWNTREND

    # Everything else is sideways
    return SIDEWAYS


def _get_vix_level() -> float | None:
    """Try to get current VIX level."""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        logger.debug(f"Could not fetch VIX: {e}")
    return None


def load_regime() -> dict:
    """Load the most recent regime classification from disk."""
    try:
        with open(REGIME_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_regime("No regime data on disk")


def _default_regime(reason: str) -> dict:
    """Return a conservative default regime."""
    return {
        "regime": SIDEWAYS,
        "timestamp": datetime.now().isoformat(),
        "signals": {"note": reason},
        "parameters": config.REGIME_PARAMS.get(SIDEWAYS, {
            "max_position_pct": 0.15,
            "stop_atr_multiplier": 2.0,
            "strategy_note": "Sideways — reduce size, favor mean reversion",
        }),
    }


def get_regime_summary() -> str:
    """Build a text summary of the current regime for the LLM prompt."""
    regime_data = load_regime()
    regime = regime_data.get("regime", "UNKNOWN")
    params = regime_data.get("parameters", {})
    signals = regime_data.get("signals", {})

    lines = [
        f"\n### Market Regime: {regime}\n",
        f"- Max position size: {params.get('max_position_pct', 0.25) * 100:.0f}%",
        f"- Stop ATR multiplier: {params.get('stop_atr_multiplier', 2.0)}x",
        f"- Strategy: {params.get('strategy_note', 'N/A')}",
    ]

    if signals.get("vix") is not None:
        lines.append(f"- VIX: {signals['vix']}")
    if signals.get("rsi") is not None:
        lines.append(f"- SPY RSI: {signals['rsi']}")
    if signals.get("roc_20") is not None:
        lines.append(f"- SPY 20d ROC: {signals['roc_20']}%")
    if signals.get("golden_cross") is not None:
        lines.append(f"- SMA 50/200: {'Golden Cross' if signals['golden_cross'] else 'Death Cross'}")

    return "\n".join(lines)
