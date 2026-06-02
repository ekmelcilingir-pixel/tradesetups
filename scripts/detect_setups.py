"""Detect swing-trade setups from daily OHLCV and compute entry/stop/targets.

This is a transparent, tunable baseline — NOT a guaranteed edge. It classifies
each holding into one of: Bull Flag, Breakout, Pullback, Bounce (or None) and
returns the structured facts the report needs. Tune the thresholds to taste.
"""
from indicators import ema, sma, rsi, atr, last


def _pct(a, b):
    return round((b - a) / a * 100, 1) if a else 0.0


def analyze(d):
    """d = output of fetch_data.get_history. Returns a facts dict or None."""
    closes, highs, lows, vols = d["closes"], d["highs"], d["lows"], d["volumes"]
    n = len(closes)
    px = closes[-1]
    e20 = last(ema(closes, 20))
    e50 = last(ema(closes, 50))
    s200 = last(sma(closes, 200)) or last(sma(closes, min(200, n - 1)))
    r = last(rsi(closes, 14)) or 50
    a = atr(highs, lows, closes, 14) or (px * 0.03)
    vol = vols[-1] if vols else 0
    vol_avg = sum(vols[-50:]) / max(1, len(vols[-50:])) if vols else 0
    vol_x = round(vol / vol_avg, 1) if vol_avg else 0
    day_chg = _pct(closes[-2], closes[-1]) if n >= 2 else 0.0

    hi20 = max(highs[-20:])
    lo20 = min(lows[-20:])
    hi60 = max(highs[-60:]) if n >= 60 else hi20
    range_band = (round(min(lows[-15:]), 2), round(max(highs[-15:]), 2))

    setup, score, note = None, 0, ""
    uptrend = e50 and s200 and px > e50 and e50 > s200

    # --- Breakout: closing at/above prior consolidation high on volume ---
    prior_hi = max(highs[-40:-1]) if n > 41 else hi20
    if px >= prior_hi and vol_x >= 1.3 and r < 80:
        setup, score, note = "Breakout", 80 + (vol_x - 1.3) * 10, "breakout above multi-week base on volume"
    # --- Bull Flag: strong run then tight hold near highs ---
    elif uptrend and 52 <= r <= 78 and (hi20 - lo20) / px < 0.16 and px > e20:
        run = _pct(min(closes[-25:-8]) if n > 25 else closes[0], max(closes[-10:]))
        if run > 12:
            setup, score, note = "Bull Flag", 70 + min(run, 40) * 0.4, "tight consolidation after a strong advance"
    # --- Pullback: uptrend dip toward EMA20 with cooled RSI ---
    if setup is None and uptrend and 33 <= r <= 56 and px <= e20 * 1.03:
        setup, score, note = "Pullback", 65 + (56 - r) * 0.4, "pullback into EMA20 within an uptrend"
    # --- Bounce: oversold then attempting to turn ---
    if setup is None and r < 32 and day_chg > 0:
        setup, score, note = "Bounce", 55, "oversold reversal attempt"

    if setup is None:
        return {"ticker": d["ticker"], "setup": None, "rsi": round(r), "px": round(px, 2),
                "day_chg": day_chg, "vol_x": vol_x}

    # ---- entry / stop / targets (ATR + structure aware) ----
    if setup == "Pullback":
        entry_lo, entry_hi = round(e20 * 0.99, 0), round(e20 * 1.01, 0)
        stop = round(entry_lo - 1.0 * a, 0)
        t1 = round(max(highs[-15:]), 0)
        t2 = round(t1 + 1.5 * a, 0)
    elif setup == "Breakout":
        entry_lo, entry_hi = round(prior_hi * 0.99, 0), round(prior_hi * 1.01, 0)
        stop = round(prior_hi - 1.2 * a, 0)
        t1 = round(px + 1.5 * a, 0)
        t2 = round(px + 3.0 * a, 0)
    elif setup == "Bull Flag":
        entry_lo, entry_hi = round(range_band[0] + (range_band[1] - range_band[0]) * 0.3, 0), round(range_band[1] * 0.99, 0)
        stop = round(range_band[0] - 0.5 * a, 0)
        t1 = round(range_band[1] + 1.0 * a, 0)
        t2 = round(range_band[1] + 2.5 * a, 0)
    else:  # Bounce
        entry_lo, entry_hi = round(px, 0), round(px + 0.4 * a, 0)
        stop = round(min(lows[-5:]) - 0.5 * a, 0)
        t1 = round(e20, 0)
        t2 = round(e20 + 1.5 * a, 0)

    mid_entry = (entry_lo + entry_hi) / 2
    risk = max(mid_entry - stop, 0.01)
    rwd = ((t1 - mid_entry) + (t2 - mid_entry)) / 2
    rr = round(rwd / risk, 2)
    rr_class = "iyi" if rr >= 2.4 else ("orta" if rr >= 1.6 else "orta")
    rr_label = "Strong" if rr >= 2.4 else "Medium"

    return {
        "ticker": d["ticker"], "setup": setup, "score": round(score, 1), "note": note,
        "px": round(px, 2), "rsi": round(r), "ema20": round(e20), "ema50": round(e50),
        "sma200": round(s200) if s200 else None, "atr": round(a, 2),
        "vol_x": vol_x, "day_chg": day_chg,
        "entry_lo": int(entry_lo), "entry_hi": int(entry_hi), "stop": int(stop),
        "t1": int(t1), "t2": int(t2),
        "t1_pct": _pct(mid_entry, t1), "t2_pct": _pct(mid_entry, t2),
        "stop_pct": _pct(mid_entry, stop),
        "rr": rr, "rr_class": rr_class, "rr_label": rr_label,
        "risk": round(risk, 1), "reward": round(rwd, 1),
        "range_lo": range_band[0], "range_hi": range_band[1],
        "closes30": [round(c, 2) for c in closes[-30:]],
    }


def rank(facts_list, top=5):
    have = [f for f in facts_list if f.get("setup")]
    have.sort(key=lambda f: f["score"], reverse=True)
    return have[:top], have[top:]
