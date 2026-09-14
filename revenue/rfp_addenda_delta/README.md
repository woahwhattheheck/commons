# Exact RFP / Addenda Delta Desk

A buyer packet is not static. Base solicitations gain addenda, Q&A, revised pricing
forms, replacement exhibits, accelerated/extended deadlines, and corrected
mandatory requirements. Reusing an old compliance matrix after one of those changes
is a commercial failure mode.

This package is an **offline evidence product** that compares two exact
buyer-source generations and produces a deterministic owner-review delta. It answers:

- which controlling documents were added, removed, or changed;
- which requirement identities were added, removed, changed, or unchanged;
- whether an apparent same-ID change has an exact supersession lineage;
- which prior human review decisions are still attached to byte/semantic-identical
  requirements; and
- which rows must be reviewed again before later bid/submission work can continue.

It does not contact a buyer, acknowledge an addendum, sign a form, submit a bid,
commit price/staffing, move money, or recognize revenue.

## Schemas

`commons-rfp-source-generation/v1` carries one opportunity/generation, its exact
source inventory, and normalized requirement identities. Requirements may bind only
to `OFFICIAL` documents. `SECONDARY` sources may be retained as discovery metadata
but cannot control a requirement.

A controlling document change reusing the same `document_id` must carry the exact
prior document SHA-256 in `supersedes_sha256`. A buyer may publish a replacement
under a new document ID; that is valid only when the new row names the exact SHA-256
of one and only one removed predecessor. One-to-many successors and digest-ambiguous
predecessors are `CONFLICT`. A requirement change reusing the same `requirement_id`
must carry the exact prior statement SHA-256 in `supersedes_sha256`. Quiet same-ID
rewrites are `CONFLICT`.

`commons-rfp-review-decision/v1` is optional prior review evidence. It binds the old
opportunity, old source generation, exact normalized requirement identity, decision
ID/time, and evidence digest. It is never inferred from prose.

## States

- `NO_MATERIAL_CHANGE`: source semantics are materially unchanged and every
  non-informational live requirement has valid carried review coverage.
- `REVIEW_REQUIRED`: material packet/requirement movement occurred or current
  non-informational requirements lack exact review coverage.
- `SOURCE_REFRESH_REQUIRED`: the new source set is declared incomplete or the
  captured generation is older than the fixed seven-day evidence ceiling.
- `CONFLICT`: exact supersession/source continuity is broken.
- `HOLD`: reserved by the v1 report contract for future fail-closed operational
  extensions; malformed input raises `DeltaError` rather than minting a report.

A `NO_MATERIAL_CHANGE` receipt is evidence-only. It is not submission authority.

## CLI

```bash
python -m revenue.rfp_addenda_delta.cli compile \
  --old old-generation.json \
  --new new-generation.json \
  --decisions prior-decisions.json \
  --out-json delta-receipt.json \
  --out-md delta-report.md

python -m revenue.rfp_addenda_delta.cli verify \
  --old old-generation.json \
  --new new-generation.json \
  --decisions prior-decisions.json \
  --report delta-receipt.json
```

The current-work CLI owns process UTC. It accepts bounded regular files, preflights
both output paths before publishing either artifact, and then writes create-exclusively.
Existing paths, duplicate output paths, and final-component symlinks are refused. A
late filesystem race can still yield a truthful partial publication; the CLI never
pathname-deletes a created artifact during rollback.

Exit codes for `compile`: 0 only for `NO_MATERIAL_CHANGE`, 3 for a truthful non-green
review state, 2 for malformed/custody failure. `verify` returns 0 only for exact
recompilation validity.

## Validation

Focused hostile coverage exercises addenda/form additions, requirement and source
supersession, deadline/mandatory/route/cure drift, source-set shrink, stale/future
sources, cross-generation decisions, duplicate IDs/JSON keys, bool/int traps,
noncanonical timestamps, URL credential injection, order determinism, receipt
tamper/reseal, create-exclusive output, and final-component symlink refusal.

Synthetic acceptance:

```bash
python -m revenue.rfp_addenda_delta.synthetic_acceptance
```

Expected semantics: unchanged reviewed generation => `NO_MATERIAL_CHANGE`; a newly
added controlling addendum/mandatory row => `REVIEW_REQUIRED`; a superseded changed
mandatory row => `REVIEW_REQUIRED`.

## Commercial use

This can support a bounded **RFP/Addenda Delta Review** service: ingest two
buyer-controlled packet generations, publish an evidence-bound change report, and
hand the client exact rows requiring renewed technical/commercial/legal/security
review. Price, contract scope, source access, and buyer/client authority remain owner
decisions; this repository does not claim a sale merely because the product exists.
