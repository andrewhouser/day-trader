"""Market data fetching module using yfinance with optional Finnhub real-time quotes."""
import logging
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import yfinance as yf

import config

logger = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

# Tickers eligible for Finnhub quotes (ETFs only; indices use different
# symbology on Finnhub and the free tier may not support them).
_FINNHUB_ELIGIBLE = set(config.INSTRUMENTS.keys())


def get_finnhub_quote(symbol: str) -> tuple[dict | None, str]:
    """Fetch a real-time quote from Finnhub's /quote endpoint.

    Returns (quote_dict, source_label).  *quote_dict* contains the raw
    JSON fields (c, h, l, d, dp, pc) when the call succeeds, or *None*
    on any failure.  The caller decides which fields to use.
    """
    if not FINNHUB_KEY:
        return None, "unavailable"
    try:
        resp = requests.get(
            f"{FINNHUB_BASE}/quote",
            params={"symbol": symbol, "token": FINNHUB_KEY},
            timeout=10,
        )
        if resp.status_code == 429:
            logger.warning(f"[finnhub] rate-limited on quote for {symbol}")
            return None, "unavailable"
        resp.raise_for_status()
        data = resp.json()
        price = data.get("c")
        if not price:
            return None, "unavailable"
        return data, "finnhub_live"
    except Exception as exc:
        logger.debug(f"[finnhub] quote error for {symbol}: {exc}")
        return None, "unavailable"


def _get_live_price(ticker: yf.Ticker, ticker_sym: str) -> tuple[float | None, str]:
    """Try to get the most current price using a multi-level fallback.
    Returns (price, source) where source is 'finnhub_live', 'live',
    'intraday', or 'daily_close'."""
    # Level 0: Finnhub real-time quote (ETFs only, skipped when key is unset)
    if FINNHUB_KEY and ticker_sym in _FINNHUB_ELIGIBLE:
        fh_data, fh_src = get_finnhub_quote(ticker_sym)
        if fh_data is not None:
            price = round(float(fh_data["c"]), 2)
            logger.debug(f"{ticker_sym}: live price ${price:.2f} via finnhub_live")
            return price, fh_src

    # Level 1: fast_info (real-time quote)
    try:
        price = ticker.fast_info.get("last_price") or ticker.fast_info.get("lastPrice")
        if price and price > 0:
            logger.debug(f"{ticker_sym}: live price ${price:.2f} via fast_info")
            return round(float(price), 2), "live"
    except Exception:
        pass

    # Level 2: latest 1-minute bar
    try:
        hist_1m = ticker.history(period="1d", interval="1m")
        if not hist_1m.empty:
            price = float(hist_1m["Close"].iloc[-1])
            logger.debug(f"{ticker_sym}: intraday price ${price:.2f} via 1m bar")
            return round(price, 2), "intraday"
    except Exception:
        pass

    # Level 3: daily close fallback
    try:
        hist_d = ticker.history(period="5d")
        if not hist_d.empty:
            price = float(hist_d["Close"].iloc[-1])
            logger.debug(f"{ticker_sym}: daily close ${price:.2f} via 5d history")
            return round(price, 2), "daily_close"
    except Exception:
        pass

    return None, "unavailable"


def fetch_index_levels() -> dict:
    """Fetch current levels for all tracked indices."""
    results = {}
    for symbol, name in config.INDICES.items():
        try:
            ticker = yf.Ticker(symbol)

            # Get live price via fallback chain
            current, price_source = _get_live_price(ticker, symbol)

            # Get prior daily close for change calculation
            hist = ticker.history(period="2d")
            if current is None:
                if hist.empty:
                    logger.warning(f"No data for {symbol} ({name})")
                    results[name] = {"symbol": symbol, "error": "No data available"}
                    continue
                current = round(float(hist["Close"].iloc[-1]), 2)
                price_source = "daily_close"

            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
            change = current - prev
            change_pct = (change / prev) * 100 if prev else 0

            results[name] = {
                "symbol": symbol,
                "price": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "price_source": price_source,
                "timestamp": hist.index[-1].isoformat() if not hist.empty else datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            results[name] = {"symbol": symbol, "error": str(e)}
    return results


def fetch_instrument_prices() -> dict:
    """Fetch current prices for all tradeable instruments."""
    results = {}
    for ticker_sym, info in config.INSTRUMENTS.items():
        try:
            ticker = yf.Ticker(ticker_sym)

            # --- Attempt Finnhub quote first (gives price + h/l/d/dp) ---
            fh_data: dict | None = None
            if FINNHUB_KEY and ticker_sym in _FINNHUB_ELIGIBLE:
                fh_data, fh_src = get_finnhub_quote(ticker_sym)

            if fh_data is not None:
                current = round(float(fh_data["c"]), 2)
                price_source = fh_src
                logger.debug(f"{ticker_sym}: live price ${current:.2f} via finnhub_live")
                # Use Finnhub's intraday fields directly
                high = round(float(fh_data.get("h") or current), 2)
                low = round(float(fh_data.get("l") or current), 2)
                change = round(float(fh_data.get("d") or 0), 2)
                change_pct = round(float(fh_data.get("dp") or 0), 2)
            else:
                # Fall back to yfinance price chain
                current, price_source = _get_live_price(ticker, ticker_sym)
                high = None
                low = None
                change = None
                change_pct = None

            # Get 5d daily history for momentum and volume (always from yfinance)
            hist_5d = ticker.history(period="5d")

            if current is None:
                if hist_5d.empty:
                    results[ticker_sym] = {"error": "No data available"}
                    continue
                current = round(float(hist_5d["Close"].iloc[-1]), 2)
                price_source = "daily_close"

            # Compute change from yfinance when Finnhub didn't supply it
            if change is None:
                prev = float(hist_5d["Close"].iloc[-2]) if len(hist_5d) > 1 else current
                change = round(current - prev, 2)
                change_pct = round((change / prev) * 100 if prev else 0, 2)

            # 5-day momentum from daily bars
            if len(hist_5d) >= 5:
                five_day_change = ((current - float(hist_5d["Close"].iloc[0])) / float(hist_5d["Close"].iloc[0])) * 100
            else:
                five_day_change = 0

            # Volume + fallback high/low when Finnhub wasn't used
            if high is None or low is None:
                hist_today = ticker.history(period="1d", interval="1d")
                if not hist_today.empty:
                    high = high or round(float(hist_today["High"].iloc[-1]), 2)
                    low = low or round(float(hist_today["Low"].iloc[-1]), 2)
                    volume = int(hist_today["Volume"].iloc[-1]) if "Volume" in hist_today else None
                elif not hist_5d.empty:
                    high = high or round(float(hist_5d["High"].iloc[-1]), 2)
                    low = low or round(float(hist_5d["Low"].iloc[-1]), 2)
                    volume = int(hist_5d["Volume"].iloc[-1]) if "Volume" in hist_5d else None
                else:
                    high = high or current
                    low = low or current
                    volume = None
            else:
                # Finnhub supplied high/low; still need volume from yfinance
                hist_today = ticker.history(period="1d", interval="1d")
                if not hist_today.empty:
                    volume = int(hist_today["Volume"].iloc[-1]) if "Volume" in hist_today else None
                elif not hist_5d.empty:
                    volume = int(hist_5d["Volume"].iloc[-1]) if "Volume" in hist_5d else None
                else:
                    volume = None

            results[ticker_sym] = {
                "type": info["type"],
                "tracks": info["tracks"],
                "price": round(current, 2),
                "change": change,
                "change_pct": change_pct,
                "five_day_change_pct": round(five_day_change, 2),
                "volume": volume,
                "high": high,
                "low": low,
                "price_source": price_source,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching {ticker_sym}: {e}")
            results[ticker_sym] = {"error": str(e)}
    return results


def get_market_summary() -> str:
    """Build a text summary of current market conditions for the LLM."""
    indices = fetch_index_levels()
    instruments = fetch_instrument_prices()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [f"## Market Data as of {now}\n", "### Index Levels\n"]
    for name, data in indices.items():
        if "error" in data:
            lines.append(f"- {name} ({data['symbol']}): {data['error']}")
        else:
            direction = "▲" if data["change"] >= 0 else "▼"
            lines.append(
                f"- {name} ({data['symbol']}): {data['price']} "
                f"{direction} {data['change']} ({data['change_pct']:+.2f}%) "
                f"[{data.get('price_source', 'unknown')}]"
            )

    lines.append("\n### Tradeable Instruments\n")
    for sym, data in instruments.items():
        if "error" in data:
            lines.append(f"- {sym}: {data['error']}")
        else:
            direction = "▲" if data["change"] >= 0 else "▼"
            lines.append(
                f"- {sym} ({data['tracks']}): ${data['price']} "
                f"{direction} {data['change']} ({data['change_pct']:+.2f}%) | "
                f"5d: {data['five_day_change_pct']:+.2f}% | "
                f"Vol: {data.get('volume', 'N/A')} | "
                f"H: ${data['high']} L: ${data['low']} "
                f"[{data.get('price_source', 'unknown')}]"
            )

    return "\n".join(lines)


def fetch_technical_indicators() -> dict:
    """Compute technical indicators for each instrument using pandas_ta.
    Fetches 250 days of daily history to ensure enough data for SMA 200.
    Returns a dict keyed by ticker with all indicator values."""
    try:
        import pandas_ta as ta
    except ImportError:
        logger.error("pandas_ta not installed, falling back to manual calculations")
        ta = None

    results = {}
    all_tickers = list(config.INSTRUMENTS.keys())

    for ticker_sym in all_tickers:
        try:
            ticker = yf.Ticker(ticker_sym)
            hist = ticker.history(period="1y")
            if hist.empty or len(hist) < 30:
                results[ticker_sym] = {"error": "Insufficient data"}
                continue

            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]
            volume = hist["Volume"]

            indicators = {}

            if ta is not None:
                sma20 = ta.sma(close, length=20)
                sma50 = ta.sma(close, length=50)
                sma200 = ta.sma(close, length=200)
                indicators["sma_20"] = round(float(sma20.iloc[-1]), 2) if sma20 is not None and not sma20.empty and pd.notna(sma20.iloc[-1]) else None
                indicators["sma_50"] = round(float(sma50.iloc[-1]), 2) if sma50 is not None and not sma50.empty and pd.notna(sma50.iloc[-1]) else None
                indicators["sma_200"] = round(float(sma200.iloc[-1]), 2) if sma200 is not None and not sma200.empty and pd.notna(sma200.iloc[-1]) else None

                ema12 = ta.ema(close, length=12)
                ema26 = ta.ema(close, length=26)
                indicators["ema_12"] = round(float(ema12.iloc[-1]), 2) if ema12 is not None and not ema12.empty and pd.notna(ema12.iloc[-1]) else None
                indicators["ema_26"] = round(float(ema26.iloc[-1]), 2) if ema26 is not None and not ema26.empty and pd.notna(ema26.iloc[-1]) else None

                rsi = ta.rsi(close, length=14)
                indicators["rsi_14"] = round(float(rsi.iloc[-1]), 2) if rsi is not None and not rsi.empty and pd.notna(rsi.iloc[-1]) else None

                macd_df = ta.macd(close, fast=12, slow=26, signal=9)
                if macd_df is not None and not macd_df.empty:
                    cols = macd_df.columns
                    indicators["macd"] = round(float(macd_df[cols[0]].iloc[-1]), 4) if pd.notna(macd_df[cols[0]].iloc[-1]) else None
                    indicators["macd_signal"] = round(float(macd_df[cols[1]].iloc[-1]), 4) if pd.notna(macd_df[cols[1]].iloc[-1]) else None
                    indicators["macd_histogram"] = round(float(macd_df[cols[2]].iloc[-1]), 4) if pd.notna(macd_df[cols[2]].iloc[-1]) else None

                bb = ta.bbands(close, length=20, std=2)
                if bb is not None and not bb.empty:
                    bb_cols = bb.columns
                    indicators["bb_lower"] = round(float(bb[bb_cols[0]].iloc[-1]), 2) if pd.notna(bb[bb_cols[0]].iloc[-1]) else None
                    indicators["bb_mid"] = round(float(bb[bb_cols[1]].iloc[-1]), 2) if pd.notna(bb[bb_cols[1]].iloc[-1]) else None
                    indicators["bb_upper"] = round(float(bb[bb_cols[2]].iloc[-1]), 2) if pd.notna(bb[bb_cols[2]].iloc[-1]) else None

                atr = ta.atr(high, low, close, length=14)
                indicators["atr_14"] = round(float(atr.iloc[-1]), 4) if atr is not None and not atr.empty and pd.notna(atr.iloc[-1]) else None
            else:
                indicators["sma_20"] = round(float(close.rolling(20).mean().iloc[-1]), 2) if len(close) >= 20 else None
                indicators["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
                indicators["sma_200"] = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None
                indicators["ema_12"] = round(float(close.ewm(span=12).mean().iloc[-1]), 2)
                indicators["ema_26"] = round(float(close.ewm(span=26).mean().iloc[-1]), 2)

                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi_series = 100 - (100 / (1 + rs))
                indicators["rsi_14"] = round(float(rsi_series.iloc[-1]), 2) if pd.notna(rsi_series.iloc[-1]) else None

                ema12_s = close.ewm(span=12).mean()
                ema26_s = close.ewm(span=26).mean()
                macd_line = ema12_s - ema26_s
                signal_line = macd_line.ewm(span=9).mean()
                indicators["macd"] = round(float(macd_line.iloc[-1]), 4)
                indicators["macd_signal"] = round(float(signal_line.iloc[-1]), 4)
                indicators["macd_histogram"] = round(float((macd_line - signal_line).iloc[-1]), 4)

                sma20_s = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                if len(close) >= 20:
                    indicators["bb_lower"] = round(float((sma20_s - 2 * std20).iloc[-1]), 2)
                    indicators["bb_mid"] = round(float(sma20_s.iloc[-1]), 2)
                    indicators["bb_upper"] = round(float((sma20_s + 2 * std20).iloc[-1]), 2)

                if len(hist) >= 15:
                    tr1 = high - low
                    tr2 = (high - close.shift()).abs()
                    tr3 = (low - close.shift()).abs()
                    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                    atr_val = tr.rolling(14).mean().iloc[-1]
                    indicators["atr_14"] = round(float(atr_val), 4) if pd.notna(atr_val) else None

            # Volume ratio
            if len(volume) >= 20 and volume.iloc[-1] > 0:
                avg_vol = volume.rolling(20).mean().iloc[-1]
                indicators["volume_ratio"] = round(float(volume.iloc[-1] / avg_vol), 2) if avg_vol > 0 else None
            else:
                indicators["volume_ratio"] = None

            indicators["price"] = round(float(close.iloc[-1]), 2)

            if len(close) >= 20:
                roc = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100
                indicators["roc_20"] = round(float(roc), 2)
            else:
                indicators["roc_20"] = None

            results[ticker_sym] = indicators

        except Exception as e:
            logger.error(f"Error computing technicals for {ticker_sym}: {e}")
            results[ticker_sym] = {"error": str(e)}

    return results


def get_technicals_summary() -> str:
    """Build a text summary of technical indicators for the LLM prompt."""
    technicals = fetch_technical_indicators()
    lines = ["\n### Technical Indicators\n"]

    for ticker, data in technicals.items():
        if "error" in data:
            lines.append(f"- {ticker}: {data['error']}")
            continue

        price = data.get("price", "N/A")
        sma20 = data.get("sma_20", "N/A")
        sma50 = data.get("sma_50", "N/A")
        sma200 = data.get("sma_200", "N/A")
        rsi = data.get("rsi_14", "N/A")
        macd_h = data.get("macd_histogram", "N/A")
        atr = data.get("atr_14", "N/A")
        bb_lower = data.get("bb_lower", "N/A")
        bb_upper = data.get("bb_upper", "N/A")
        vol_ratio = data.get("volume_ratio", "N/A")
        roc = data.get("roc_20", "N/A")

        trend = "N/A"
        if all(v is not None for v in [data.get("sma_20"), data.get("sma_50"), data.get("sma_200")]):
            if data["sma_20"] > data["sma_50"] > data["sma_200"]:
                trend = "BULLISH (20>50>200)"
            elif data["sma_20"] < data["sma_50"] < data["sma_200"]:
                trend = "BEARISH (20<50<200)"
            else:
                trend = "MIXED"

        lines.append(
            f"- {ticker} @ ${price} | SMA 20/50/200: {sma20}/{sma50}/{sma200} | "
            f"Trend: {trend} | RSI: {rsi} | MACD Hist: {macd_h} | "
            f"ATR: {atr} | BB: [{bb_lower}-{bb_upper}] | "
            f"Vol Ratio: {vol_ratio} | ROC(20d): {roc}%"
        )

    return "\n".join(lines)
