# InfiniteCAL cross-state method parity LIMS — build receipt

Task: `infinitecal-crossstate-method-parity-lims-01`
Builder: SOL-INFINITECAL / ChatGPT cloud seat
Date: 2026-09-09

## Scope

Synthetic/read-only parity bridge for California, Michigan, and New York. The same 20 blinded materials are represented in each state; each material carries three analytes. The bridge compares immutable method/result provenance without writing to a state system, declaring compliance, contacting a prospect, or releasing a CoA.

All outputs remain `STAGED_HUMAN_REVIEW`. Automatic or anonymous release is rejected; release requires a non-empty named reviewer and does not mutate the original ledger entry.

## Frozen fixture and acceptance

Fixture recipe: `fixtures/infinitecal_180_records.json` (deterministically expands to 180 immutable synthetic records)

- 180 records total: 60 CA + 60 MI + 60 NY.
- Expected outcomes: 150 `PARITY_CLEAN`; 12 `METHOD_VERSION_MISMATCH`; 9 `UNIT_ROUNDING_MISMATCH`; 6 `DUPLICATE_ACCESSION`; 3 `MISSING_SOURCE_FILE`.
- Holds stage no draft.
- Clean rows preserve canonical analyte/unit/LOQ/result hashes while retaining state-specific rule-pack/method lineage.
- No accepted accession is reused by another state/material record.
- Full same-ledger replay is idempotent and adds zero processed records, accepted rows, holds, drafts, or events.

Fixture SHA-256: `44328084e81680382eb11c9701de8b287a9cc6ec27ca613c5c33f0c926de636a`
Manifest SHA-256: `d7c0c2436eeb3b80637af13e2c99e26576b080c6e7437403ac4e7b0262255b3e`

## Verification actually run

Python: `/usr/bin/python3` (Python 3.13 in this cloud seat)

- `python3 -m py_compile infinitecal_parity.py test_infinitecal_parity.py` — PASS.
- `python3 test_infinitecal_parity.py -v` — 16/16 PASS.
- `python3 infinitecal_parity.py --fixture fixtures/infinitecal_180_records.json` — PASS with exact status counts: 150 clean / 30 holds (12 / 9 / 6 / 3), state counts 60 / 60 / 60, ledger 180 processed / 150 accepted / 30 holds / 150 drafts / 180 events, and replay delta 0 for every ledger collection.
- Anonymous-release regression — PASS (rejected).
- Named-human-release regression — PASS; returned released copy leaves stored staged record unchanged.
- Fixture-tamper regression — PASS (hash mismatch rejected).

`clean_parity_keys=60`: all 20 materials × 3 analytes retain at least one clean state row after seeded faults, and every clean cross-state occurrence of a key has exactly one canonical analyte/unit/LOQ/result-hash tuple.

## Authored file hashes

- `README.md` — SHA-256 `9f727d0f1018c6f1a1157dc7bd4f4e084522f6cc8fcff1a3a8be8e7df3a235c4`
- `infinitecal_parity.py` — SHA-256 `d9e6878538ed6fde12a29d82b6d6bdd44651880a8b49d896aa84045d725276b6`
- `test_infinitecal_parity.py` — SHA-256 `bb027a7b312da43ca8dddcb1922b7490cf6e79836ccd916b6b39fe3ea9f8114b`
- `fixtures/infinitecal_180_records.json` — SHA-256 `44328084e81680382eb11c9701de8b287a9cc6ec27ca613c5c33f0c926de636a`
- `fixtures/manifest.json` — SHA-256 `d7c0c2436eeb3b80637af13e2c99e26576b080c6e7437403ac4e7b0262255b3e`

## Publication boundary

This receipt freezes authored bytes and local acceptance evidence before publication. PR/head/merge/current-main readback receipts are posted in the canonical Slack build-demand thread after guarded publication; this file does not self-edit to manufacture a merge receipt.

No state/provider/customer/production write, compliance decision, outreach, prospect-facing demo, payment/spend action, automatic CoA release, owner-PC action, force-push, or reset was performed.
