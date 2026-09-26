"""The comparison the spec asks for, on 200 held-out receipts that never touch training:
schema validity, field-level accuracy, p95 latency and cost per 1,000, for the rule-based
baseline and the trained extractor (with one ablation: without position features)."""
import json
import random
import time
from pathlib import Path

import numpy as np

from . import data
from .extract import Trained, rules
from .schema import clean, same, validate

RESULTS = Path(__file__).resolve().parent.parent / "results"
FIELDS = ("company", "date", "address", "total")
HOST_PER_HOUR = 0.08925          # one 2-vCPU cloud machine (AWS c7i.large on-demand)


def score(extract, receipts):
    rows, times = [], []
    for r in receipts:
        start = time.perf_counter()
        x = extract(r)
        times.append(time.perf_counter() - start)
        ok, errors = validate(x)
        rows.append({"valid": ok, **{f: same(f, x.get(f), r["gold"].get(f, "")) for f in FIELDS}})
    p95 = float(np.percentile(times, 95))
    return {"valid": float(np.mean([r["valid"] for r in rows])), **{f: float(np.mean([r[f] for r in rows])) for f in FIELDS},
            "all_fields": float(np.mean([all(r[f] for f in FIELDS) for r in rows])), "p95_ms": 1000 * p95,
            "cost_per_1000": HOST_PER_HOUR / 3600 * float(np.mean(times)) * 1000}


def bench(seed=0):
    rs = data.receipts()
    order = list(range(len(rs)))
    random.Random(seed).shuffle(order)
    test, train = [rs[i] for i in order[:200]], [rs[i] for i in order[200:]]
    def reachable(r, field):
        """Could any extractor reading this OCR get the field exactly right? (Some run of consecutive rows is it.)"""
        texts, gold = [t for t, _ in r["lines"]], clean(r["gold"].get(field, ""))
        return any(clean(" ".join(texts[i:j])) == gold for i in range(len(texts)) for j in range(i + 1, min(i + 7, len(texts) + 1)))
    ceiling = {f: float(np.mean([reachable(r, f) for r in test])) for f in ("company", "address")}
    results = {"rules": score(rules, test)}
    for n in (100, 200, len(train)):
        results[f"trained ({n} receipts)"] = score(Trained().fit(train[:n]), test)
    results[f"trained, no position features ({len(train)})"] = score(Trained(positions=False).fit(train), test)
    pct = lambda x: f"{100 * x:.1f}%"
    lines = [f"200 held-out receipts; {len(train)} for training.", "",
             "| Extractor | Schema-valid | Company | Date | Address | Total | All four right | p95 latency | Cost per 1,000 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, v in results.items():
        lines.append(f"| {name} | {pct(v['valid'])} | " + " | ".join(pct(v[f]) for f in FIELDS) +
                     f" | {pct(v['all_fields'])} | {v['p95_ms']:.1f} ms | ${v['cost_per_1000']:.6f} |")
    lines += ["", f"OCR ceiling (some run of OCR rows matches the label exactly, so an extractor could get it right): "
              f"company {pct(ceiling['company'])}, address {pct(ceiling['address'])}."]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "bench.md").write_text("\n".join(lines) + "\n")
    (RESULTS / "summary.json").write_text(json.dumps({"results": results, "ocr_ceiling": ceiling}, indent=1))
    return "\n".join(lines)
