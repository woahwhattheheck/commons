# Filing Quality Desk

Offline analyst-QA tooling for **retained SEC Company Facts-shaped JSON** plus an explicit analyst policy. The product is intentionally read-only and source-bound: it selects exact facts, preserves filing/accession lineage, surfaces ambiguity and changed reported values, runs exact-decimal arithmetic checks, and emits a reproducible review bundle.

## What it does

- Selects by **taxonomy + concept + exact unit + exact fact dates**. Instant facts are keyed by exact `end`; duration facts require exact `start` and `end`.
- Applies an inclusive `filed` cutoff and then considers the latest admitted filing date. If that date has multiple **different values**, selection is refused as `AMBIGUOUS_LATEST_FILING_DATE`; multiple accessions with the same value are retained without arbitrary accession preference.
- Preserves `fy`, `fp`, and `frame` as metadata only. They never substitute for fact dates.
- Emits every admitted observation and flags `REPORTED_VALUE_CHANGED_ACROSS_FILINGS` when values differ across retained filing dates. That finding is deliberately **not called a restatement**.
- Runs user-authored arithmetic checks with Python `Decimal`, explicit coefficients, and nonnegative inclusive tolerances. A check HOLDs rather than silently comparing incompatible units or periods.
- Emits canonical `report.json`, `observations.csv`, `exceptions.csv`, self-contained `analyst.html`, and `receipt.json`; bundle verification recompiles from the exact source and policy bytes and rejects tampering.
- Rejects duplicate JSON keys, non-finite values, booleans in numeric fields, bad dates, extreme numeric precision/magnitude, CIK mismatch, unknown policy fields, unsafe shape changes, excessive input size/depth/nodes, and output overwrite.

## Boundary

The retained input bytes are **not authenticated as SEC-origin by this tool**. A filing-date filter over a later Company Facts snapshot is not a true historical-vintage or intraday-availability backtest. Custom/dimensional facts, missing concepts, issuer-specific taxonomy choices, materiality, accounting interpretation, and source-filing review remain analyst responsibilities. SHA-256 receipts prove byte identity, not issuer/SEC authenticity. The package has no authority for brokerage/trading, regulatory filing, general-ledger or payment mutation, customer-account mutation, materiality judgment, or accounting conclusions.

## Policy shape

`example_policy.json` is executable documentation. Root fields are exact:

- `schema`: `TJL_FILING_QUALITY_POLICY_V1`
- `cik`: 1–10 digits, normalized to 10-digit CIK
- `filing_cutoff`: `YYYY-MM-DD`
- `selections`: exact fact selectors
- `comparisons`: left/right selected-value comparisons; units must match
- `checks`: exact-decimal linear arithmetic checks; all inputs must share exact unit and exact period

A check expresses:

`sum(coefficient_i * selection_i) == target ± tolerance`

All coefficients/tolerances are decimal strings in normalized output. The tolerance is inclusive and must be nonnegative.

## Run

From the repository root:

```bash
python -m revenue.filing_quality_desk.cli compile \
  revenue/filing_quality_desk/example_companyfacts.json \
  revenue/filing_quality_desk/example_policy.json \
  /tmp/filing-quality-output

python -m revenue.filing_quality_desk.cli verify \
  revenue/filing_quality_desk/example_companyfacts.json \
  revenue/filing_quality_desk/example_policy.json \
  /tmp/filing-quality-output
```

The compiler refuses a non-empty output directory. Verification requires the exact retained source and policy bytes that produced the bundle.

## Tests

```bash
python -m unittest revenue.filing_quality_desk.test_engine
python -O -m unittest revenue.filing_quality_desk.test_engine
python -m py_compile revenue/filing_quality_desk/*.py
```

The synthetic suite covers cutoff behavior, exact period matching, `fy`/`fp`/`frame` non-authority, same-day differing-value ambiguity, same-value multi-accession retention, changed-reported-value language, exact Decimal pass/fail tolerances, incompatible unit/period HOLDs, CIK mismatch, duplicate/nonfinite/bool/oversized numerics, receipt tamper, byte-bound recompilation, HTML escaping, bundle tamper, no-overwrite, CLI compile→verify, and normal/optimized execution.

## Commercial use

The issue carrier (#15849) frames a bounded financial-data ingestion QA pilot: run a retained issuer cohort through this selector/checker, deliver discrepancy and lineage reports, integrate the policy/verification shape into an existing research or reporting pipeline, and transfer tests/runbook. Any buyer contact, quote, acceptance, invoice, booked revenue, or cash claim is outside this package and requires separate live authorization/evidence.
