function ema(values, period) {
  const k = 2 / (period + 1);
  let prev = values[0];
  const out = [];
  for (let i = 0; i < values.length; i++) {
    if (i === 0) { prev = values[0]; }
    else { prev = values[i] * k + prev * (1 - k); }
    out.push(prev);
  }
  return out;
}

function renderChart(containerId, closes, entryLow, entryHigh, stop, t1, t2) {
  const W = 600, H = 180;
  const padL = 20, padR = 60, padT = 12, padB = 28;
  const plotW = W - padL - padR, plotH = H - padT - padB;

  const ema20arr = ema(closes, 20);
  const ema50arr = ema(closes, 50);

  // Y range: include all key levels + price
  const allVals = closes.concat(ema20arr, ema50arr, [entryLow, entryHigh, stop, t1, t2]);
  let yMin = Math.min.apply(null, allVals);
  let yMax = Math.max.apply(null, allVals);
  const pad = (yMax - yMin) * 0.06;
  yMin -= pad; yMax += pad;

  function x(i) { return padL + (i / (closes.length - 1)) * plotW; }
  function y(p) { return padT + (1 - (p - yMin) / (yMax - yMin)) * plotH; }

  // Build SVG
  let svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" style="width:100%;height:180px;display:block;background:#0a0e14;border-radius:4px">';

  // Grid (4 horizontal lines)
  for (let i = 1; i <= 4; i++) {
    const gy = padT + (i / 5) * plotH;
    svg += '<line x1="' + padL + '" y1="' + gy + '" x2="' + (W - padR) + '" y2="' + gy + '" stroke="#1f2937" stroke-width="1" stroke-dasharray="2,4"/>';
  }

  // Y-axis labels (right side, 3 levels)
  const lvls = [yMax - pad, (yMin + yMax) / 2, yMin + pad];
  lvls.forEach((v, idx) => {
    const ly = y(v);
    svg += '<text x="' + (W - padR + 4) + '" y="' + (ly + 3) + '" fill="#6b7280" font-size="10" font-family="monospace">' + v.toFixed(0) + '</text>';
  });

  // Entry band (green fill)
  const yEH = y(entryHigh), yEL = y(entryLow);
  svg += '<rect x="' + padL + '" y="' + yEH + '" width="' + plotW + '" height="' + (yEL - yEH) + '" fill="#10b981" fill-opacity="0.13"/>';
  svg += '<line x1="' + padL + '" y1="' + yEH + '" x2="' + (W - padR) + '" y2="' + yEH + '" stroke="#10b981" stroke-width="1" stroke-opacity="0.5"/>';
  svg += '<line x1="' + padL + '" y1="' + yEL + '" x2="' + (W - padR) + '" y2="' + yEL + '" stroke="#10b981" stroke-width="1" stroke-opacity="0.5"/>';

  // Stop (red dashed)
  const yS = y(stop);
  svg += '<line x1="' + padL + '" y1="' + yS + '" x2="' + (W - padR) + '" y2="' + yS + '" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,3"/>';
  svg += '<text x="' + (W - padR + 4) + '" y="' + (yS + 3) + '" fill="#ef4444" font-size="10" font-weight="bold">Stop</text>';

  // T1, T2 (green dashed)
  const yT1 = y(t1), yT2 = y(t2);
  svg += '<line x1="' + padL + '" y1="' + yT1 + '" x2="' + (W - padR) + '" y2="' + yT1 + '" stroke="#10b981" stroke-width="1.5" stroke-dasharray="6,3"/>';
  svg += '<text x="' + (W - padR + 4) + '" y="' + (yT1 + 3) + '" fill="#10b981" font-size="10" font-weight="bold">H1</text>';
  svg += '<line x1="' + padL + '" y1="' + yT2 + '" x2="' + (W - padR) + '" y2="' + yT2 + '" stroke="#10b981" stroke-width="1.5" stroke-dasharray="6,3" stroke-opacity="0.55"/>';
  svg += '<text x="' + (W - padR + 4) + '" y="' + (yT2 + 3) + '" fill="#10b981" font-size="10" font-weight="bold" opacity="0.7">H2</text>';

  // Entry label
  svg += '<text x="' + (W - padR + 4) + '" y="' + ((yEH + yEL) / 2 + 3) + '" fill="#10b981" font-size="10" font-weight="bold">Entry</text>';

  // EMA20 (yellow dashed)
  let p20 = '';
  ema20arr.forEach((v, i) => { p20 += (i === 0 ? 'M' : 'L') + x(i) + ',' + y(v); });
  svg += '<path d="' + p20 + '" stroke="#f59e0b" stroke-width="1.5" fill="none" stroke-dasharray="4,3"/>';

  // EMA50 (purple dashed)
  let p50 = '';
  ema50arr.forEach((v, i) => { p50 += (i === 0 ? 'M' : 'L') + x(i) + ',' + y(v); });
  svg += '<path d="' + p50 + '" stroke="#a78bfa" stroke-width="1.5" fill="none" stroke-dasharray="4,3"/>';

  // Price polyline (blue solid)
  let pP = '';
  closes.forEach((v, i) => { pP += (i === 0 ? 'M' : 'L') + x(i) + ',' + y(v); });
  svg += '<path d="' + pP + '" stroke="#60a5fa" stroke-width="2.2" fill="none"/>';

  // Current price dot
  const lastIdx = closes.length - 1;
  svg += '<circle cx="' + x(lastIdx) + '" cy="' + y(closes[lastIdx]) + '" r="5" fill="#60a5fa"/>';
  svg += '<circle cx="' + x(lastIdx) + '" cy="' + y(closes[lastIdx]) + '" r="9" fill="none" stroke="#60a5fa" stroke-width="1" opacity="0.4"/>';

  // Legend bottom-left
  const legY = H - 8;
  svg += '<g font-size="10" font-family="-apple-system,sans-serif">';
  svg += '<line x1="' + padL + '" y1="' + legY + '" x2="' + (padL+12) + '" y2="' + legY + '" stroke="#60a5fa" stroke-width="2.2"/>';
  svg += '<text x="' + (padL+16) + '" y="' + (legY+3) + '" fill="#8b949e">Price</text>';
  svg += '<line x1="' + (padL+60) + '" y1="' + legY + '" x2="' + (padL+72) + '" y2="' + legY + '" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4,3"/>';
  svg += '<text x="' + (padL+76) + '" y="' + (legY+3) + '" fill="#8b949e">EMA20</text>';
  svg += '<line x1="' + (padL+125) + '" y1="' + legY + '" x2="' + (padL+137) + '" y2="' + legY + '" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,3"/>';
  svg += '<text x="' + (padL+141) + '" y="' + (legY+3) + '" fill="#8b949e">EMA50</text>';
  svg += '</g>';

  svg += '</svg>';
  document.getElementById(containerId).innerHTML = svg;
}