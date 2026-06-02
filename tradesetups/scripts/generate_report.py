"""Daily tradesetups generator.

Pipeline:
  1. Load portfolio.json
  2. Fetch ~6mo daily candles per holding (Yahoo)
  3. Detect + rank swing setups (top 5)
  4. Ask Claude to write the narrative blocks (JSON) from the computed facts
  5. Render the master-format HTML report
  6. Write reports/<file>.html and update reports/manifest.json

Env:
  ANTHROPIC_API_KEY   required
  MODEL               optional (default claude-sonnet-4-6)
  FMP_API_KEY         optional (latest quote)
  PRICE_IN_PER_MTOK   optional float -> enables $ cost in manifest
  PRICE_OUT_PER_MTOK  optional float
"""
import os
import sys
import json
import time
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_data           # noqa: E402
import detect_setups        # noqa: E402
import universe as universe_mod  # noqa: E402
import render as renderer    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")
MANIFEST = os.path.join(REPORTS, "manifest.json")
MODEL = os.getenv("MODEL", "claude-sonnet-4-6")

PROMPT = """You are a disciplined swing-trading desk analyst. I give you pre-computed
technical facts for {n} setups detected from a portfolio. Write concise, English,
plain-text narrative blocks for each. Use the exact numbers I provide; do not invent
new price levels. Tone: pragmatic, specific, no hype. No HTML, no markdown.

For EACH setup return:
  entry_note   (<=6 words, what the entry zone represents, e.g. "EMA20 retest, range mid")
  range_note   (<=8 words, e.g. "10 trading days, late May")
  option       (one line options idea, e.g. "Long calls ~0.45 delta, 4-6 week expiry")
  trigger      (2-4 sentences: what set it up + the concrete trigger condition)
  playbook     (2-3 sentences: scale-in, where to bank half, where stop goes, invalidation)
  in_short     (one punchy sentence)
  validity     (e.g. "Validity: 5 business days. Voided if the trigger doesn't come.")

Also return:
  top_summary  (1-2 sentences summarising the day across all setups)
  so_what      (1-2 sentences, the disciplined takeaway)
  skipped      (object mapping each skipped ticker to a <=20-word reason)

Return ONLY a JSON object with keys: "setups" (object keyed by ticker), "top_summary",
"so_what", "skipped". No prose outside the JSON.

FACTS:
{facts}
SKIPPED (no setup): {skipped}
"""


def call_claude(picks, skipped):
    from anthropic import Anthropic
    client = Anthropic()
    facts = {f["ticker"]: {k: f[k] for k in (
        "setup", "px", "rsi", "ema20", "ema50", "sma200", "atr", "vol_x", "day_chg",
        "entry_lo", "entry_hi", "stop", "t1", "t2", "t1_pct", "t2_pct", "stop_pct",
        "rr", "risk", "reward", "range_lo", "range_hi", "note")} for f in picks}
    skip = {f["ticker"]: {"day_chg": f["day_chg"], "rsi": f["rsi"]} for f in skipped}
    msg = PROMPT.format(n=len(picks), facts=json.dumps(facts, indent=1),
                        skipped=json.dumps(skip))
    t0 = time.time()
    resp = client.messages.create(
        model=MODEL, max_tokens=4000,
        messages=[{"role": "user", "content": msg}],
    )
    dur = time.time() - t0
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip()
    data = json.loads(text)
    usage = resp.usage
    return data, {
        "dur": dur,
        "in": usage.input_tokens,
        "out": usage.output_tokens,
    }


def cost_str(tin, tout):
    pin, pout = os.getenv("PRICE_IN_PER_MTOK"), os.getenv("PRICE_OUT_PER_MTOK")
    if not (pin and pout):
        return "—"
    c = tin / 1e6 * float(pin) + tout / 1e6 * float(pout)
    return f"${c:.3f}"


def load_manifest():
    if os.path.exists(MANIFEST):
        try:
            return json.load(open(MANIFEST, encoding="utf-8"))
        except Exception:
            pass
    return {"reports": []}


def main():
    extra = []
    pf_path = os.path.join(ROOT, "portfolio.json")
    if os.path.exists(pf_path):
        try:
            extra = [h["ticker"] for h in json.load(open(pf_path, encoding="utf-8")).get("holdings", [])]
        except Exception:
            extra = []

    universe = universe_mod.get_universe(extra=extra)
    tagmap = {u["ticker"]: u["tag"] for u in universe}
    tickers = [u["ticker"] for u in universe]
    print(f"Scanning {len(tickers)} tickers (S&P 500 + Nasdaq-100 + Dow + holdings)...")

    facts = []
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def work(tk):
        d = fetch_data.get_history(tk)
        if not d:
            return None
        f = detect_setups.analyze(d)
        f["index_tag"] = tagmap.get(tk, "")
        return f

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(work, tk): tk for tk in tickers}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                facts.append(r)

    picks, _rest = detect_setups.rank(facts, top=5)
    if not picks:
        print("No setups today; nothing generated.")
        return
    # keep the report's "skipped" note short: biggest movers with no setup
    no_setup = [f for f in facts if not f.get("setup")]
    no_setup.sort(key=lambda f: abs(f.get("day_chg", 0)), reverse=True)
    skipped = no_setup[:6]

    data, meta = call_claude(picks, skipped)
    narratives = data.get("setups", {})
    narratives["_skipped"] = data.get("skipped", {})

    now = dt.datetime.now()
    rmeta = {
        "date_iso": now.strftime("%Y-%m-%d"),
        "date_human": now.strftime("%B %-d, %Y") if os.name != "nt" else now.strftime("%B %d, %Y"),
        "generated_human": now.strftime("%d.%m.%Y %H:%M:%S"),
        "scanned": len(facts),
    }
    html_out = renderer.render(rmeta, picks, skipped, narratives,
                               data.get("top_summary", ""), data.get("so_what", ""))

    os.makedirs(REPORTS, exist_ok=True)
    fname = f"tradesetups-{rmeta['date_iso']}-{int(time.time()*1000)}.html"
    with open(os.path.join(REPORTS, fname), "w", encoding="utf-8") as f:
        f.write(html_out)

    man = load_manifest()
    man["reports"] = [r for r in man["reports"] if r["date"] != rmeta["date_iso"]]
    man["reports"].append({
        "date": rmeta["date_iso"],
        "gen": rmeta["generated_human"],
        "status": "ready",
        "dur": f"{meta['dur']/60:.1f} min" if meta['dur'] >= 60 else f"{meta['dur']:.1f} s",
        "cost": cost_str(meta["in"], meta["out"]),
        "size": f"{len(html_out)/1024:.1f} KB",
        "tok": f"{meta['in']:,} / {meta['out']:,}",
        "file": fname,
    })
    man["reports"].sort(key=lambda r: r["date"], reverse=True)
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=2)
    print(f"Generated {fname} · {len(picks)} setups · manifest now has {len(man['reports'])} reports")


if __name__ == "__main__":
    main()
