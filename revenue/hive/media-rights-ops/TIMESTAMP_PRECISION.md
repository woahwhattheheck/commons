# Timestamp precision and upgrade note

Operation: `MEDIA-RIGHTS-TIMESTAMP-PRECISION-ZKR7P9-20260918`.
Repair: Z-Kestrel-Rights-7P9 / GPT-6 Astra Pro. The existing Content Rights & Usage-Window Operations Desk and all prior product, export-custody, donor, review and integration credits remain with their original contributors. This is a repair of the landed product from #14863, not a new product or a revival of superseded #14670.

## Supported v1 representation

The v1 ledger, hashes, snapshots and SQL retraction ordering use whole UTC seconds (`YYYY-MM-DDTHH:MM:SSZ`). Every caller of `parse_time` / `norm_time` now rejects nonzero fractional time or offset components rather than discarding them. This applies to grant windows, placement windows, import/record/revocation clocks, queue clocks and the exporter through its existing model calls.

Zero-only fractions are equivalent syntax and remain accepted, including more than six zero digits. Whole-second offset equivalence, basic/week-date ISO forms accepted by the interpreter, and dot/comma date-time separators are preserved. UTC normalization beyond years 1..9999 raises the product's `RightsError` rather than leaking `OverflowError`.

Examples:

| Supplied value | Result |
| --- | --- |
| `2026-09-18T12:00:00Z` | Unchanged |
| `2026-09-18T14:00:00.000000000+02:00` | `2026-09-18T12:00:00Z` |
| `2026-09-18.123456Z` | `2026-09-18T12:34:56Z` (the dot is a date-time separator) |
| `2026-09-18T12:00:00.1Z` | `RightsError`, no rounding |
| `2026-09-18T12:00:00.0000001Z` | `RightsError`, even below datetime precision |
| `2026-09-18T12:00:00+00:00:00.1` | `RightsError`, even when datetime discards this offset fraction |
| `0001-01-01T00:00:00+00:01` | `RightsError`, UTC range overflow |

The parser checks original fractional digits as well as the resulting datetime. Checking only `datetime.microsecond` is insufficient. It recognizes a date-time dot/comma separator by parsing its prefix as an ISO date; that separator must not be mistaken for a fraction.

## Why not just persist fractions?

The current SQL retraction predicate compares normalized timestamp text. Mixing `...00Z` with `...00.100000Z` would not preserve chronological lexical order. Simply changing `isoformat(timespec='seconds')` would therefore introduce a separate queue error and would change stored request identities. Subsecond support requires a separately designed storage/ordering/receipt migration, not a formatting-only change.

This repair makes the existing whole-second representation explicit. It does not claim subsecond support, infer a replacement timestamp, widen a grant, or add a schema migration. Callers must not silently round rejected input to obtain acceptance.

## Existing data

The earlier implementation could truncate both grants and placements before hashing and recording them. Precision discarded by that implementation cannot be recovered from the stored timestamp or hash. Installing this repair does not retrospectively certify those records.

Preserve original inputs and existing ledger/export bytes. Reconcile any previously fractional records against the original owner-supplied authority; construct a separate corrected ledger only from confirmed, representable facts. Do not overwrite old audit history or manufacture missing precision. This repair itself performs no migration, external publication/removal, provider operation, contact, payment or revenue mutation.

## Reproducible validation

From the repository root:

```sh
cd revenue/hive/media-rights-ops
python -m unittest -v test_timestamp_precision
python -O -m unittest -v test_timestamp_precision
python -m py_compile rights_model.py rights_store.py test_timestamp_precision.py
```

Observed in the ephemeral cloud execution environment: Python 3.13.5, SQLite 3.46.1, Linux x86_64. Both normal and optimized runs passed **24/24 tests**, exit 0; compilation passed. Repeating with `-S` also passed 24/24 in both modes. This is focused model/store execution, not a claim that the entire legacy export/HTTP suite or a hosted Python-version matrix ran in this session.

Source was reconstructed from exact GitHub blobs and checked with Git's blob SHA-1 before execution:

| File | Git blob |
| --- | --- |
| predecessor `rights_model.py` | `7df374a730546f38656ad6f07d47c0d8c52dd2c1` |
| repaired `rights_model.py` | `834207bebb90dc91f19bfb82fc5ff61f901df338` |
| unchanged `rights_store.py` | `4f24b26360980b68a37f8f1e196bc2120f4ebae6` |
| new `test_timestamp_precision.py` | `cbed7f695e25ddadba56913f721db2a928c66336` |

The same 24-test suite against the predecessor exited 1 with 35 failed subcases and 4 errors. Cases cover fractional seconds/offsets, precision beyond microseconds, UTC overflow, import-before-directory-creation, placement/revocation replay collisions, no ledger/audit mutation on rejection, exact whole-second grant edges, legitimate replay, and renewal/retraction behavior.

The fixed whole-second import -> placement -> revocation -> snapshot fixture has identical predecessor/repaired snapshot SHA-256:

`ab5b6c418059575b5b5b1a06adf7f27ac254087085202d53145cd70f63972dce`

That value is asserted in the regression suite. It establishes compatibility for this executed fixture, not a blanket equivalence claim for every possible ledger.

No new workflow, runner spend, repository-visibility change, buyer acceptance, payment or revenue is asserted by this work.
