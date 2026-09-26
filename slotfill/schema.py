"""The strict schema: an extraction either validates or it does not.

company and address: non-empty text. date: a real calendar date, returned as YYYY-MM-DD
whatever the receipt's format. total: a positive amount with two decimals. Comparisons
normalise case, spacing and trailing punctuation, and compare dates and totals as values."""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
DATE = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})|(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})|"
                  r"(\d{1,2})\s*[-/ ]?\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*[-/ ]?\s*(\d{2,4})", re.I)
AMOUNT = re.compile(r"(?<![\d.])(\d{1,6}(?:,\d{3})*\.\d{2})(?![\d])")


def parse_date(text):
    """The first real date in the text, as YYYY-MM-DD, or None."""
    for m in DATE.finditer(text or ""):
        g = m.groups()
        try:
            if g[0]:
                d, mo, y = int(g[0]), int(g[1]), int(g[2])
            elif g[3]:
                y, mo, d = int(g[3]), int(g[4]), int(g[5])
            else:
                d, mo, y = int(g[6]), MONTHS[g[7][:3].upper()], int(g[8])
            y += 2000 if y < 100 else 0
            return date(y, mo, d).isoformat()
        except (ValueError, KeyError):
            continue
    return None


def parse_amount(text):
    found = AMOUNT.findall(text or "")
    return f"{float(found[-1].replace(',', '')):.2f}" if found else None


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"[.,;:]+$", "", (text or "").upper())).strip()


def validate(x):
    """(valid, errors) for {"company", "date", "address", "total"}."""
    errors = [f"{k} is empty" for k in ("company", "address") if not (x.get(k) or "").strip()]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.get("date") or "") or parse_date(x.get("date")) != x.get("date"):
        errors.append("date is not a real YYYY-MM-DD date")
    if not re.fullmatch(r"\d+\.\d{2}", x.get("total") or "") or float(x["total"]) <= 0:
        errors.append("total is not a positive amount with two decimals")
    return not errors, errors


def same(field, got, gold):
    if field == "date":
        return got is not None and got == parse_date(gold)
    if field == "total":
        g = parse_amount(gold) or (f"{float(gold):.2f}" if re.fullmatch(r"\d+(\.\d+)?", gold or "") else None)
        return got is not None and got == g
    return clean(got) == clean(gold)
