"""Build the daily scan universe from index constituents.

Source of truth: universe/indices.json (S&P 500 + Nasdaq-100 + Dow 30), shipped
in the repo so the job never depends on scraping at runtime. If FMP_API_KEY is
set, we best-effort refresh the lists from FMP first; on any failure we fall back
to the shipped file.
"""
import os
import json
import requests

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDICES = os.path.join(HERE, "universe", "indices.json")

CODE = {"sp500": "SPX", "nasdaq100": "NDX", "dow": "DJIA"}
FMP = {
    "sp500": "https://financialmodelingprep.com/api/v3/sp500_constituent?apikey={k}",
    "nasdaq100": "https://financialmodelingprep.com/api/v3/nasdaq_constituent?apikey={k}",
    "dow": "https://financialmodelingprep.com/api/v3/dowjones_constituent?apikey={k}",
}


def _norm(sym):
    return str(sym).strip().upper().replace(".", "-")


def _refresh_fmp():
    key = os.getenv("FMP_API_KEY")
    if not key:
        return None
    out = {}
    for idx, url in FMP.items():
        try:
            r = requests.get(url.format(k=key), timeout=20)
            r.raise_for_status()
            rows = r.json()
            syms = [_norm(x.get("symbol")) for x in rows if x.get("symbol")]
            if len(syms) < (25 if idx == "dow" else 80):
                return None  # looks wrong / not entitled -> bail to fallback
            out[idx] = sorted(set(syms))
        except Exception:
            return None
    return out


def load_indices():
    data = _refresh_fmp()
    if data:
        return data
    with open(INDICES, encoding="utf-8") as f:
        return json.load(f)


def get_universe(extra=None):
    """Return list of {ticker, indices:[...], tag:'SPX NDX'} deduped.

    `extra` = optional iterable of extra tickers (e.g. your own holdings) that
    will always be included even if not in an index.
    """
    idx = load_indices()
    membership = {}
    for name in ("sp500", "nasdaq100", "dow"):
        for t in idx.get(name, []):
            membership.setdefault(t, []).append(name)
    for t in (extra or []):
        membership.setdefault(_norm(t), []).append("watch")

    universe = []
    for t in sorted(membership):
        codes = [CODE[m] for m in membership[t] if m in CODE]
        tag = " ".join(codes) if codes else "WATCH"
        universe.append({"ticker": t, "indices": membership[t], "tag": tag})
    return universe
