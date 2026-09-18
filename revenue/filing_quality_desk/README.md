# Filing Quality Desk

Offline analyst-QA tooling for retained SEC Company Facts JSON. It selects exact taxonomy/concept/unit/period observations under an explicit filing-date cutoff, refuses same-day differing-value ambiguity, records prior values without calling them restatements, evaluates typed same-unit/same-period arithmetic checks, and emits deterministic JSON/CSV/HTML plus a byte-verifiable manifest.

**Boundaries:** supplied bytes are not authenticated SEC custody; filtering a later snapshot by filing date is not a historical-vintage guarantee; no investment, filing, trading, GL, payment, or customer-account action is authorized.

## Policy

```json
{"cik":"123456","filed_on_or_before":"2026-09-01","selectors":[{"id":"assets","taxonomy":"us-gaap","concept":"Assets","unit":"USD","kind":"instant","end":"2026-06-30"},{"id":"liabilities","taxonomy":"us-gaap","concept":"Liabilities","unit":"USD","kind":"instant","end":"2026-06-30"},{"id":"equity","taxonomy":"us-gaap","concept":"StockholdersEquity","unit":"USD","kind":"instant","end":"2026-06-30"}],"checks":[{"id":"balance","kind":"sum_equals","lhs":["liabilities","equity"],"rhs":"assets","tolerance":0}]}
```

JSON numbers are parsed lexically into exact `Decimal` values. Duplicate keys, non-finite values, bool-as-number, unknown policy fields, mismatched CIKs, unsupported/missing facts, incompatible units/periods, and ambiguous latest filing-day values fail closed.

## CLI / proof

```bash
python -m revenue.filing_quality_desk.engine compile --source companyfacts.json --policy policy.json --out out
python -m revenue.filing_quality_desk.engine verify --source companyfacts.json --policy policy.json --out out
python -m unittest revenue.filing_quality_desk.test_engine
python -O -m unittest revenue.filing_quality_desk.test_engine
```

Outputs: `packet.json`, `observations.csv`, `findings.csv`, escaped `report.html`, and `manifest.json`.

A paid pilot can map a buyer's retained issuer cohort and analyst policy into this selector, deliver reproducible discrepancy/lineage reports, integrate it with an existing data pipeline, and transfer the tests/runbook. No buyer, quote, acceptance, invoice, booked revenue, or cash is implied here.
