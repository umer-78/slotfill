"""The prompted path: any OpenAI-compatible model asked for the schema as JSON, validated by
the same strict schema. Not measured in this repository (it runs without API keys); run it on
the same 200 held-out receipts before choosing between it and the trained extractor."""
import json
import urllib.request

from .schema import parse_amount, parse_date

PROMPT = ("Extract the store's company name, date, address and total from this receipt's OCR text. Correct obvious OCR "
          "misspellings in the company name and address. Reply with JSON: {\"company\", \"date\", \"address\", \"total\"}.\n\n")


def prompted(model, base_url, api_key):
    def extract(r):
        body = {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": PROMPT + "\n".join(t for t, _ in r["lines"])}]}
        req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            x = json.loads(json.loads(resp.read())["choices"][0]["message"]["content"])
        return {"company": x.get("company", ""), "address": x.get("address", ""),
                "date": parse_date(str(x.get("date", ""))), "total": parse_amount(str(x.get("total", "")))}
    return extract
