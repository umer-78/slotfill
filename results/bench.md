200 held-out receipts; 426 for training.

| Extractor | Schema-valid | Company | Date | Address | Total | All four right | p95 latency | Cost per 1,000 |
|---|---|---|---|---|---|---|---|---|
| rules | 83.5% | 60.5% | 97.0% | 31.5% | 69.0% | 13.0% | 0.2 ms | $0.000003 |
| trained (100 receipts) | 98.5% | 63.5% | 98.0% | 59.0% | 86.0% | 35.5% | 5.1 ms | $0.000072 |
| trained (200 receipts) | 98.5% | 63.0% | 98.0% | 66.5% | 90.5% | 41.0% | 3.3 ms | $0.000060 |
| trained (426 receipts) | 98.5% | 64.0% | 98.0% | 67.5% | 94.0% | 44.0% | 3.8 ms | $0.000067 |
| trained, no position features (426) | 98.0% | 62.5% | 98.0% | 62.0% | 94.0% | 41.0% | 3.9 ms | $0.000069 |

OCR ceiling (some run of OCR rows matches the label exactly, so an extractor could get it right): company 73.5%, address 80.5%.
