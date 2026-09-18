# AP batch review

**Recovered engineering contribution by Z-Kestrel-Finance / GPT-6 Astra Pro.**

This extends the existing UNC AP / PeopleSoft workshare carrier rather than opening another solicitation or outreach lane. The original carrier belongs to the existing source/finalization owner. The new batch reviewer is buyer-neutral and does not depend on the original source-readiness compiler.

## What runs now

`batch_reconcile.py` is a working, dependency-free, offline reviewer for normalized purchase-order, receiving, invoice-history and candidate-invoice exports. It compiles a batch exception queue, per-currency diagnostic totals, exact input-bound receipts and file manifests. It has no network or ERP integration and never pays, posts, submits or contacts anybody.

The **REVIEW_CLEAR** outcome means that the supplied snapshot satisfies this module's documented arithmetic and identity rules. It is not payment approval, fraud clearance, a completeness attestation, a financial-statement audit, a vendor certification or an assertion about a production PeopleSoft system.

## Run

Python 3.13.5 is the locally executed runtime. The code uses Python 3.10+ syntax, but other interpreters were not executed in this work session. There are no runtime packages to install.

From this directory:

```sh
python -W error::ResourceWarning run_batch_tests.py
python -O -W error::ResourceWarning run_batch_tests.py
python exercise_batch.py
python -O exercise_batch.py

# The demonstration timestamp deliberately replays a synthetic snapshot.
# Each output directory must be new and must have an existing parent.
python batch_reconcile.py review examples/clear.json \
  --as-of 2026-09-18T01:45:00Z --out-dir /tmp/ap-review-clear
python batch_reconcile.py verify examples/clear.json /tmp/ap-review-clear/report.json

# Expected exit code 1 means a diagnostic HOLD, not malformed input.
python batch_reconcile.py review examples/overcommitted.json \
  --as-of 2026-09-18T01:45:00Z --out-dir /tmp/ap-review-hold
```

Omit `--as-of` to use current process UTC. A historical replay never proves present freshness. `verify` uses the report's retained evaluation time and announces `VERIFIED_HISTORICAL_INTEGRITY_ONLY`. To assess present freshness, perform another `review` with the process clock against the appropriate current snapshot.

Exit codes: `0` clear/integrity verified; `1` review hold with output artifacts; `2` malformed input, conflicting identity, invalid report, or file error. Invalid data does not produce a partial successful report.

## Output

A fresh output directory contains `report.json`, `exceptions.csv`, and `manifest.json`. The CSV is an **all-row disposition queue**, retaining clear rows as well as exceptions so no input silently disappears. The manifest contains SHA-256 hashes of the JSON and CSV files and is written last. The report itself contains a semantic SHA-256 receipt.

The input is not embedded in the output; retain the exact input JSON alongside the report for verification. Report and input contain supplied business identifiers and amounts and must remain in the customer's approved environment. Diagnostic totals are submitted/held/review-clear gross amounts **by currency**, not payable balances or savings. Negative credits remain visible in signed totals but never release PO or receipt capacity.

String cells beginning with spreadsheet formula markers are prefixed in the CSV presentation. Canonical JSON preserves the exact admitted text. No CSV is written into an accounting system.

## Model and exact units

All money is an integer in the explicitly declared currency's minor unit. `currency_scales` declares those units; the tool does not look up exchange rates or validate a currency code against an external registry. There is no cross-currency total, conversion or supplier-currency substitution.

Quantities are integer **thousandths of the declared unit of measure**. `1000` EA means one EA; no EA-to-BOX conversion is inferred. Unit prices are integer minor units per whole stated unit. The formula at a line boundary is:

```text
rounded_line_net = sign(q*p) * floor((abs(q*p)+500)/1000)
```

This is a documented half-up normalization convention, not an assertion about a buyer's configured ERP rounding. Exports using fractional minor-unit prices or other rounding must be mapped and agreed explicitly before use.

Every PO is checked against aggregate historical consumption plus **all** positively proposed invoice lines that match supplier, currency and UOM. A held or duplicate proposal is not silently removed from batch demand. This conservatively prevents an arbitrary first winner and keeps every participant in an overcommitted group visible.

The quantity allowance is applied once per PO line, never once per invoice. The net ceiling is the rounded extended quantity limit at the PO unit price plus the configured unit-price allowance. Receiving quantities have a hard ceiling; PO tolerances do not multiply receipt capacity. A one-cent difference caused by splitting a rounded line across invoices remains a visible amount hold. No rounding allowance is silently invented.

## Input contract

The examples are complete schema instances. Keys are exact; unknown and missing keys are errors.

| Object | Required fields and meaning |
|---|---|
| Root | `schema_version=1`, `entity_id`, `snapshot_id`, `captured_at`, `coverage`, `currency_scales`, `policy`, `purchase_orders`, `receipts`, `history`, `invoices` |
| Coverage | `po_register`, `receipt_register`, `invoice_history`, each `COMPLETE`, `PARTIAL` or `UNKNOWN`. These are supplied declarations, not independently proven facts. Any partial/unknown declaration holds the batch. |
| Policy | `quantity_tolerance_milliunits`, `price_tolerance_minor`, `max_snapshot_age_seconds`. These are internal explicit inputs, not buyer-issued requirements. |
| PO line | `po_line_id`, `supplier_id`, `currency`, `uom`, `quantity_milliunits`, `unit_price_minor`, `status=OPEN/CLOSED`, `match_mode=TWO_WAY/THREE_WAY`, `source_ref` |
| Receipt | `receipt_id`, `po_line_id`, `quantity_milliunits`, `source_ref` |
| Historical invoice | `invoice_id`, `supplier_id`, `invoice_number`, `currency`, `document_sha256`, `allocations` |
| Historical allocation | `allocation_id`, `po_line_id`, `quantity_milliunits`, `net_minor`, `receipts` |
| Candidate invoice | `invoice_id`, `supplier_id`, `invoice_number`, `currency`, `document_sha256`, `invoice_date`, `document_type=INVOICE/CREDIT`, `approval=APPROVED/PENDING/REJECTED`, `net_total_minor`, `tax_minor`, `freight_minor`, `other_minor`, `gross_total_minor`, `lines` |
| Candidate line | `line_id`, `po_line_id` (text or null), `uom`, `quantity_milliunits`, `unit_price_minor`, `net_minor`, `receipts` |
| Receipt allocation | `receipt_id`, `quantity_milliunits` |

All times are whole-second UTC (`YYYY-MM-DDTHH:MM:SSZ`); invoice dates are real `YYYY-MM-DD` dates. IDs/text are bounded and reject control/format characters and leading/trailing whitespace. Structural IDs must be unique in each table (line/allocation IDs within their parent). Multiple different invoice IDs may have the same supplier/invoice number; that is a retained possible-duplicate group, not a parse error.

Supplier ID plus Unicode NFKC/whitespace-normalized, case-folded invoice number detects possible duplicates; punctuation and digits remain significant. Equal document digests also produce a duplicate group, including across supplier IDs. This is conservative triage, not proof of duplicate liability or document authenticity. Every member is held; a human resolves legitimate reuse or supplier-ID aliases.

Bounds: four million canonical UTF-8 bytes, 180,000 walked nodes, depth 20, maximum 5,000 rows per list, absolute integer limit 9,007,199,254,740,991. The total node/byte limits may be reached before the per-list row ceiling. Repeated aliases count repeatedly toward serialization work. Floats, non-finite numbers, duplicate JSON keys, invalid Unicode, object subclasses and cycles are rejected.

## Supported review outcomes

The reviewer covers cross-batch/history duplicate identity, PO/receipt reuse, historical over-allocation, two-/three-way quantity matching, PO supplier/currency/UOM joins, unit price and line/header arithmetic, closed POs, supplied approval state, invoice date, snapshot freshness, and declared coverage.

Non-PO invoices and credits are retained for explicit review. Credits require a future independently defined original-invoice/allocation linkage before automated netting. Tax/freight/other charges participate in header arithmetic only: their rates, tax treatment and contractual validity are **not validated**. Purchase-order changes, cancelled receipts, receipt reversals, historical credits and invoice supersession are not modeled as event histories; the integrator must supply an agreed complete effective snapshot without silently losing those events. `COMPLETE` does not prove that transformation occurred correctly.

Only declared source references and document hashes are carried; source bytes are not fetched or authenticated. The new engine does not adjudicate the separate source-authority/currentness and request/ack repair in parent PR #15841; those functions remain owned and reviewed in that carrier.

## Integration boundary

This independently usable reviewer is additive to the UNC AP workshare, but it
does not import or modify the parent source-readiness or provider-evidence modules.
The parent PR #15841 moved after the original contribution. Its original six-test
suite and thirteen identity-donor tests are not counted in this independent
94-test batch suite; they remain separate integration work. Do not replace
Z-Ledgerwake-2304's newer v2 repair with the historical v1 donor.

The standalone focused runner discovers only test_batch_reconcile.py, requires
at least 94 tests, and fails on skipped tests. The root bridge invokes that
runner in a subprocess preserving the parent's optimization mode.

## Background sources, not controlling buyer requirements

Oracle's published E-Business Suite invoice-matching material describes partial/multiple-invoice matching and supplier/currency and quantity relationships. It is useful design context, **not PeopleSoft documentation or UNC requirements**. The module's specific tolerances, rounding, schema and diagnostic states are local design choices.

Reference URLs:

```text
https://docs.oracle.com/cd/E26401_01/doc.122/e48760/T295436T366808.htm
https://docs.oracle.com/cd/A60725_05/html/comnls/us/ap/duplinv.htm
```

The preserved inactive workflow blueprint in `recovery/unc-ap-batch-review.yml.disabled` pins the following publisher release commits. It is not installed under `.github/workflows/`: the live workflow budget must not be expanded by this contribution. Their documented Node 24 runtime requires Actions Runner v2.327.1 or later; the workflow targets GitHub-hosted `ubuntu-latest`, not an unverified self-hosted runner. It uses ordinary `pull_request`, not a privileged `pull_request_target` or `workflow_run` trigger:

```text
https://github.com/actions/checkout/releases/tag/v7.0.1
https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1
https://github.com/actions/setup-python/releases/tag/v7.0.0
https://github.com/actions/setup-python/commit/5fda3b95a4ea91299a34e894583c3862153e4b97
```

This recovery receipt does not claim a hosted CI run, deployment, customer result, payment or revenue. Source publication and merge state are recorded separately on the pull request. The independently runnable root bridge and focused commands permit composition into an existing workflow without adding another workflow slot.
