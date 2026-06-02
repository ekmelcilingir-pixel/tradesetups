"""Render the daily tradesetups report HTML in the master dark-theme format."""
import os
import html

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPL = os.path.join(HERE, "templates")

with open(os.path.join(TMPL, "report_style.css"), encoding="utf-8") as f:
    CSS = f.read()
with open(os.path.join(TMPL, "report_chart.js"), encoding="utf-8") as f:
    CHART_JS = f.read()

TAG = {"Bull Flag": "bullflag", "Breakout": "breakout",
       "Pullback": "pullback", "Bounce": "bounce"}


def _card(rank, f, narr, subport, subport_label):
    pos = "pos" if f["day_chg"] >= 0 else "neg"
    sign = "+" if f["day_chg"] >= 0 else ""
    s200 = f["sma200"] if f["sma200"] is not None else "—"
    range_row = ""
    if f["setup"] in ("Pullback", "Bull Flag") or narr.get("range_note"):
        range_row = (
            f'<div class="range-row"><b>Range:</b> ${f["range_lo"]} - ${f["range_hi"]}'
            f' &nbsp;·&nbsp; <b>Time in range:</b> {html.escape(narr.get("range_note","recent consolidation"))}</div>'
        )
    option_row = ""
    if narr.get("option"):
        option_row = f'<div class="option-row"><b>Option:</b> {html.escape(narr["option"])}</div>'
    return f"""
<div class="setup-card">
  <div class="card-header">
    <div class="card-rank">{rank}</div>
    <div class="card-ticker">{f['ticker']}</div>
    <span class="subport-tag {subport.lower()}">{subport} · {subport_label}</span>
    <span class="setup-tag {TAG.get(f['setup'],'breakout')}">{f['setup']}</span>
    <span class="card-spacer"></span>
    <span class="daily-pct {pos}">{sign}{f['day_chg']}% (today)</span>
  </div>
  <div class="chart-wrap"><div id="chart-{f['ticker']}"></div></div>
  <div class="tech-row">
    <span>RSI(14) <b>{f['rsi']}</b></span>
    <span>EMA20 <b>{f['ema20']}</b></span>
    <span>EMA50 <b>{f['ema50']}</b></span>
    <span>SMA200 ~<b>{s200}</b></span>
    <span>ATR(14) <b>{f['atr']}</b></span>
    <span>Last <b>${f['px']}</b></span>
  </div>
  <div class="boxes">
    <div class="box entry"><div class="label">Entry</div><div class="val">{f['entry_lo']} - {f['entry_hi']}</div><div class="sub">{html.escape(narr.get('entry_note','entry zone'))}</div></div>
    <div class="box stop"><div class="label">Stop</div><div class="val">{f['stop']}</div><div class="sub">{f['stop_pct']}% · structure</div></div>
    <div class="box t1"><div class="label">Target 1</div><div class="val">{f['t1']}</div><div class="sub">+{f['t1_pct']}% · T1</div></div>
    <div class="box t2"><div class="label">Target 2</div><div class="val">{f['t2']}</div><div class="sub">+{f['t2_pct']}% · T2</div></div>
    <div class="box rr"><div class="label">Weighted R:R</div><div class="val">1:{f['rr']} <span class="rr-badge {f['rr_class']}">{f['rr_label']}</span></div><div class="sub">Risk ${f['risk']} / Reward ${f['reward']}</div></div>
  </div>
  {range_row}
  {option_row}
  <div class="trigger"><b>Trigger:</b> {html.escape(narr.get('trigger',''))}</div>
  <div class="playbook"><b>Playbook:</b> {html.escape(narr.get('playbook',''))}</div>
  <div class="yani-satiri">In short: {html.escape(narr.get('in_short',''))}</div>
  <div class="valid">{html.escape(narr.get('validity',''))}</div>
</div>"""


def render(meta, picks, skipped, narratives, top_summary, so_what):
    cards = "".join(
        _card(i + 1, f, narratives.get(f["ticker"], {}), f.get("subport", "P1"),
              f.get("subport_label", "Investment"))
        for i, f in enumerate(picks)
    )
    skipped_li = "".join(
        f'<li><b>{f["ticker"]}</b> ({"+" if f["day_chg"]>=0 else ""}{f["day_chg"]}%, RSI {f["rsi"]}): '
        f'{html.escape(narratives.get("_skipped", {}).get(f["ticker"], "no clean setup right now."))}</li>'
        for f in skipped
    )
    # chart data object + render loop appended to the renderer JS
    data_lines = []
    for f in picks:
        data_lines.append(
            f"  {f['ticker']}: {{ closes: {f['closes30']}, entryLow: {f['entry_lo']}, "
            f"entryHigh: {f['entry_hi']}, stop: {f['stop']}, t1: {f['t1']}, t2: {f['t2']} }}"
        )
    chart_block = (
        CHART_JS
        + "\nconst setups = {\n" + ",\n".join(data_lines) + "\n};\n"
        + "Object.keys(setups).forEach(function(k){var s=setups[k];"
        + "renderChart('chart-'+k, s.closes, s.entryLow, s.entryHigh, s.stop, s.t1, s.t2);});\n"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Today's Setups — {meta['date_human']}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<header>
  <h1>Today's Setups</h1>
  <div class="meta">{meta['generated_human']}</div>
  <div class="sub">{len(picks)} high-probability swing trade setups · {meta['scanned']} open positions scanned from the portfolio</div>
</header>
<div class="tek-cumlede">{top_summary}</div>
{cards}
<div class="skipped">
  <h3>Note — positions with no setup generated</h3>
  <ul>{skipped_li or '<li>All scanned positions produced a setup today.</li>'}</ul>
</div>
<div class="yani-nedir"><b>So what?</b> {so_what}</div>
<div class="disclaimer">
  <b>Risk warning:</b> This report is not investment advice. All numbers are computed from past price data; they do not guarantee the future. Stick to the stop stated in each setup. Size your position so that <b>1-2% of the total portfolio</b> is at risk (Risk = entry − stop). If you don't trust/like a setup, don't take it.
</div>
<details class="glossary">
  <summary>Glossary (term explanations)</summary>
  <div class="term"><b>EMA20 / EMA50:</b> <span>Exponentially weighted average price of the last 20 / 50 days; shows trend direction.</span></div>
  <div class="term"><b>SMA200:</b> <span>Simple average of the last 200 days; the main trend filter.</span></div>
  <div class="term"><b>RSI(14):</b> <span>14-day momentum index (0-100). &lt;30 oversold, &gt;70 overbought.</span></div>
  <div class="term"><b>ATR(14):</b> <span>14-day average true range = typical daily move; the unit for stops/targets.</span></div>
  <div class="term"><b>Weighted R:R:</b> <span>Average reward per unit of risk assuming a half-and-half exit at T1 and T2.</span></div>
</details>
<footer>
  Tradesetups pipeline · auto-generated daily<br>
  Data: Yahoo daily candles (last ~6 months) + portfolio.json<br>
  Generated at: {meta['generated_human']}
</footer>
</div>
<script>
{chart_block}
</script>
</body>
</html>"""
