import { $, bars, esc, fail, kpis, legend, load, num, pct, seg, table, xy } from './kit.js';

// slotfill/schema.py's parse_date and parse_amount
const MONTHS = Object.fromEntries(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'].map((m, i) => [m, i + 1]));
const DATE = /(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})|(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})|(\d{1,2})\s*[-/ ]?\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*[-/ ]?\s*(\d{2,4})/gi;
const AMOUNT = /(?<![\d.])(\d{1,6}(?:,\d{3})*\.\d{2})(?!\d)/g;
const leap = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
export function parseDate(text) {
  for (const m of (text || '').matchAll(DATE)) {
    let d, mo, y;
    if (m[1]) [d, mo, y] = [+m[1], +m[2], +m[3]];
    else if (m[4]) [y, mo, d] = [+m[4], +m[5], +m[6]];
    else [d, mo, y] = [+m[7], MONTHS[m[8].slice(0, 3).toUpperCase()], +m[9]];
    if (y < 100) y += 2000;
    const days = [31, leap(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1];
    if (y >= 1 && mo >= 1 && mo <= 12 && d >= 1 && d <= days) return `${String(y).padStart(4, '0')}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
  }
  return null;
}
export function parseAmount(text) {
  const found = [...(text || '').matchAll(AMOUNT)].map((m) => m[1]);
  return found.length ? parseFloat(found[found.length - 1].replace(/,/g, '')).toFixed(2) : null;
}

try {
  const d = await load();
  const R = d.results, rules = R.rules, best = R['trained (426 receipts)'];
  kpis($('#kpis'), [
    { label: 'All four fields right', value: pct(best.all_fields), note: `trained extractor; rules ${pct(rules.all_fields)}` },
    { label: 'Total right', value: pct(best.total), note: `rules ${pct(rules.total)}` },
    { label: 'Schema-valid output', value: pct(best.valid), note: `rules ${pct(rules.valid)}` },
    { label: 'Company name right', value: pct(best.company), note: `the OCR text allows at most ${pct(d.ocr_ceiling.company)}: it often splits or misreads the name` },
  ]);
  const names = Object.keys(R), F = { all_fields: 'all four', company: 'company', date: 'date', address: 'address', total: 'total' };
  seg($('#field'), Object.entries(F), 'all_fields', (f) => {
    bars($('#bars'), names.map((n) => ({ label: n, value: R[n][f], text: pct(R[n][f]), color: n === 'rules' ? 'var(--c6)' : n.includes('no position') ? 'var(--c2)' : 'var(--accent)' })), { max: 1 });
    const c = d.ocr_ceiling[f];
    $('#ceiling').textContent = c != null ? `OCR ceiling for ${f}: ${pct(c)}. An extractor over this OCR text cannot do better.` : f === 'date' || f === 'total' ? 'Dates and totals are compared as values, so no exact-text ceiling applies.' : '';
    if (c != null) $('#bars').insertAdjacentHTML('beforeend', `<div class="bar"><span class="name muted">OCR ceiling</span><span class="track" style="background:repeating-linear-gradient(90deg,var(--muted) 0 6px,transparent 6px 10px);height:2px;align-self:center;width:${100 * c}%"></span><span class="val muted">${pct(c)}</span></div>`);
  });
  const tr = [['100', R['trained (100 receipts)']], ['200', R['trained (200 receipts)']], ['426', best]];
  const series = ['all_fields', 'address', 'total'].map((f, i) => ({ name: F[f], color: ['var(--accent)', 'var(--c2)', 'var(--c5)'][i], dots: true, points: tr.map(([n, r]) => ({ x: +n, y: r[f], title: `${n} receipts: ${F[f]} ${pct(r[f])}` })) }));
  xy($('#curve'), { label: 'Accuracy by training receipts', height: 220, series, x: { min: 80, max: 450, fmt: String, ticks: [100, 200, 426], label: 'training receipts' }, y: { min: 0.3, max: 1, fmt: (v) => `${Math.round(v * 100)}%` } });
  legend($('#curveKey'), series);
  table($('#cost'), [{ key: 'n', label: 'Extractor' }, { key: 'p95', label: 'p95', num: true, fmt: (v) => `${num(v, 1)} ms` }, { key: 'c', label: '$ per 1,000', num: true, fmt: (v) => `$${v.toFixed(6)}` }],
    names.map((n) => ({ n, p95: R[n].p95_ms, c: R[n].cost_per_1000 })));

  const run = () => {
    const t = $('#line').value, dt = parseDate(t), am = parseAmount(t);
    $('#parsed').innerHTML = `<div>date<b>${dt ? esc(dt) : '—'}</b><span class="pill ${dt ? 'ok' : 'no'}">${dt ? 'a real calendar date' : 'no valid date'}</span></div>` +
      `<div>total<b>${am ? esc(am) : '—'}</b><span class="pill ${am ? 'ok' : 'no'}">${am ? 'last two-decimal amount' : 'no amount'}</span></div>`;
  };
  $('#line').oninput = run;
  $('#pform').onsubmit = (e) => { e.preventDefault(); run(); };
  const tries = ['DATE: 05/03/2018 TOTAL RM 1,234.50', '31-JAN-18 12:04', '2018-02-30 TOTAL 9.90', 'Tarikh 7 Mac 2018 JUMLAH 45.00', 'CASH 50.00 CHANGE 4.60'];
  $('#tries').innerHTML = 'Try: ' + tries.map((s) => `<button type="button" class="step" data-t="${esc(s)}">${esc(s)}</button>`).join(' ');
  $('#tries').onclick = (e) => { const b = e.target.closest('button[data-t]'); if (b) { $('#line').value = b.dataset.t; run(); } };
  run();
} catch (err) {
  fail(err);
}
