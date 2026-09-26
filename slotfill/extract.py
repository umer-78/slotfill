"""Two extractors over a receipt's OCR lines, and the hook for a third.

rules: the hand-written baseline a team starts with. The company is the first line with a
company suffix; the date is the first date; the address is the lines after the company up to
the first phone, tax or invoice line; the total is the amount on the last line that says TOTAL
(not SUBTOTAL), else the largest amount.

trained: a small model learns each line's role (company, address, date, total, other) from
labelled receipts: logistic regression on the line's character n-grams, its position on the
page, and pattern flags. Fields are then assembled from the most likely lines. Tens of
kilobytes, milliseconds per receipt on a CPU.

prompted: any OpenAI-compatible model asked for the schema as JSON (see llm.py); not measured
here, since this repository runs without API keys.
"""
import re

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .schema import AMOUNT, clean, parse_amount, parse_date

SUFFIX = re.compile(r"\b(SDN\.? ?BHD|BHD|S/B|ENTERPRISE|TRADING|PLT|RESTAURANT|STATIONERY|HARDWARE|MART|SHOP|CO\.|CORPORATION|LTD)\b", re.I)
STOP = re.compile(r"\b(TEL|PHONE|FAX|GST|TAX|INVOICE|RECEIPT|CASHIER|DATE|DOC|REG|CO\.? ?NO)\b", re.I)
ROLES = ("other", "company", "address", "date", "total")


def rules(r):
    texts = [t for t, _ in r["lines"]]
    ci = next((i for i, t in enumerate(texts) if SUFFIX.search(t)), 0)
    address = []
    for t in texts[ci + 1:]:
        if STOP.search(t) or AMOUNT.search(t):
            break
        if not re.fullmatch(r"[\d()\- ]+[A-Z]?", t):              # skip bare registration numbers
            address.append(t)
    date = next((d for d in map(parse_date, texts) if d), None)
    totals = [parse_amount(t) for t in texts if re.search(r"\bTOTAL\b", t, re.I) and not re.search(r"SUB", t, re.I) and parse_amount(t)]
    amounts = [float(a) for a in map(parse_amount, texts) if a]
    total = totals[-1] if totals else (f"{max(amounts):.2f}" if amounts else None)
    return {"company": texts[ci] if texts else "", "date": date, "address": " ".join(address), "total": total}


def roles_from_gold(r):
    """Which role each line played, from the labels: what the model learns from."""
    gold, out = r["gold"], []
    addr = clean(gold.get("address", ""))
    for text, _ in r["lines"]:
        c = clean(text)
        if c and c == clean(gold.get("company", ""))[: len(c)] and len(c) > 3:
            out.append("company")
        elif c and len(c) > 3 and c in addr:
            out.append("address")
        elif parse_date(text) and parse_date(text) == parse_date(gold.get("date", "")):
            out.append("date")
        elif parse_amount(text) and parse_amount(text) == parse_amount(gold.get("total", "")) and re.search(r"TOTAL|AMOUNT|RM", text, re.I):
            out.append("total")
        else:
            out.append("other")
    return out


class Trained:
    def __init__(self, c=4.0, positions=True):
        self.c, self.positions = c, positions

    def rows(self, receipts):
        texts, extra = [], []
        for r in receipts:
            height = max((b[3] for _, b in r["lines"]), default=1) or 1
            n = len(r["lines"])
            for i, (t, b) in enumerate(r["lines"]):
                texts.append(t)
                extra.append([b[1] / height, i / max(n - 1, 1), bool(parse_date(t)), bool(parse_amount(t)),
                              bool(re.search(r"\bTOTAL\b", t, re.I)), bool(re.search(r"SUB", t, re.I)), bool(SUFFIX.search(t)),
                              bool(STOP.search(t)), bool(re.search(r"\b\d{5}\b", t)), sum(ch.isdigit() for ch in t) / max(len(t), 1)])
        return texts, np.array(extra, float)

    def matrix(self, receipts, fit=False):
        texts, extra = self.rows(receipts)
        x = self.vec.fit_transform(texts) if fit else self.vec.transform(texts)
        return hstack([x, csr_matrix(extra if self.positions else extra[:, 2:])]).tocsr()

    def fit(self, receipts):
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, sublinear_tf=True)
        y = [role for r in receipts for role in roles_from_gold(r)]
        self.clf = LogisticRegression(C=self.c, max_iter=3000, class_weight="balanced").fit(self.matrix(receipts, fit=True), y)
        return self

    def __call__(self, r):
        p = self.clf.predict_proba(self.matrix([r]))
        col = {c: i for i, c in enumerate(self.clf.classes_)}
        texts = [t for t, _ in r["lines"]]
        best = lambda role, ok=lambda t: True: max((i for i in range(len(texts)) if ok(texts[i])), key=lambda i: p[i, col[role]], default=None)
        ci = best("company")
        di = best("date", lambda t: parse_date(t) is not None)
        ti = best("total", lambda t: parse_amount(t) is not None)
        address = [texts[i] for i in range(len(texts)) if p[i].argmax() == col["address"]]
        return {"company": texts[ci] if ci is not None else "", "date": parse_date(texts[di]) if di is not None else None,
                "address": " ".join(address), "total": parse_amount(texts[ti]) if ti is not None else None}
