"""SROIE (ICDAR 2019, scanned receipts): 626 real receipts, each with the OCR'd lines of its scan
(text and box) and its labelled company, date, address and total. Receipts stand in for
freight invoices: the same job, a fixed schema out of noisy layouts. Downloaded on first use,
from a pinned commit of the repository that redistributes it, into SLOTFILL_DATA (default
~/.cache/slotfill)."""
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://raw.githubusercontent.com/zzzDavid/ICDAR-2019-SROIE/27be4271b251c256f695acbade9a801bffe85994/data"


def cache_dir():
    path = Path(os.environ.get("SLOTFILL_DATA", Path.home() / ".cache" / "slotfill"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch(rel, tries=4):
    target = cache_dir() / rel
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(tries):
            try:
                with urllib.request.urlopen(f"{BASE}/{rel}", timeout=60) as r:
                    target.write_bytes(r.read())
                break
            except OSError:
                if attempt == tries - 1:
                    raise
                time.sleep(2 ** attempt)
    return target


def receipt(i):
    """{"id", "lines": [(text, (x0, y0, x1, y1))], "gold": {...}}"""
    lines = []
    for raw in fetch(f"box/{i:03d}.csv").read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split(",", 8)
        if len(parts) == 9 and parts[8].strip():
            xs, ys = [int(p) for p in parts[0:8:2]], [int(p) for p in parts[1:8:2]]
            lines.append((parts[8].strip(), (min(xs), min(ys), max(xs), max(ys))))
    return {"id": f"{i:03d}", "lines": rows(lines), "gold": json.loads(fetch(f"key/{i:03d}.json").read_text(encoding="utf-8"))}


def rows(boxes):
    """OCR gives one box per text segment, so "TOTAL" and "9.00" can be two boxes on one printed
    line. Boxes whose vertical centres are within half a line height join, left to right."""
    if not boxes:
        return []
    height = sorted(b[3] - b[1] for _, b in boxes)[len(boxes) // 2] or 1
    out = []
    for text, b in sorted(boxes, key=lambda tb: ((tb[1][1] + tb[1][3]) / 2, tb[1][0])):
        centre = (b[1] + b[3]) / 2
        if out and abs(centre - out[-1][2]) <= height / 2:
            segs, box, c = out[-1]
            out[-1] = (segs + [(b[0], text)], (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])), c)
        else:
            out.append(([(b[0], text)], b, centre))
    return [(" ".join(t for _, t in sorted(segs)), box) for segs, box, _ in out]


def receipts(n=626):
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(receipt, range(n)))
