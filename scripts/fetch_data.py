"""Fetch daily OHLCV history.

Primary source: Yahoo Finance chart endpoint (free, no API key, ~6 months daily).
This matches the project's known constraint that the FMP free plan covers
real-time quotes but NOT historical EOD. FMP can still be used for the latest
quote if FMP_API_KEY is set.
"""
import os
import time
import requests

YH = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=6mo&interval=1d"
FMP_QUOTE = "https://financialmodelingprep.com/api/v3/quote/{t}?apikey={k}"
UA = {"User-Agent": "Mozilla/5.0 (tradesetups-bot)"}


def get_history(ticker, retries=3):
    """Return dict with closes/highs/lows/volumes (chronological) + last price."""
    url = YH.format(t=ticker)
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            closes = q["close"]
            highs = q["high"]
            lows = q["low"]
            vols = q.get("volume", [])
            # drop trailing None (today's incomplete bar can be null)
            data = [(c, h, l, v) for c, h, l, v in zip(closes, highs, lows, vols)
                    if c is not None and h is not None and l is not None]
            closes = [d[0] for d in data]
            highs = [d[1] for d in data]
            lows = [d[2] for d in data]
            vols = [d[3] or 0 for d in data]
            if len(closes) < 30:
                raise ValueError("insufficient history")
            return {
                "ticker": ticker,
                "closes": closes,
                "highs": highs,
                "lows": lows,
                "volumes": vols,
                "last": closes[-1],
            }
        except Exception as e:  # noqa
            if attempt == retries - 1:
                print(f"[fetch] {ticker} failed: {e}")
                return None
            time.sleep(1.5 * (attempt + 1))


def get_quote_fmp(ticker):
    key = os.getenv("FMP_API_KEY")
    if not key:
        return None
    try:
        r = requests.get(FMP_QUOTE.format(t=ticker, k=key), timeout=15)
        r.raise_for_status()
        data = r.json()
        return data[0] if data else None
    except Exception:
        return None
