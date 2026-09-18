# InfiniteCAL named-human release-gate repair

Operation: `infinitecal-human-gate-repair-20260909-01`
Source demand: `infinitecal-crossstate-method-parity-lims-01`
Review blocker consumed: Commons PR #11139 review `5157173560`

## Scope

Bounded repair only to the existing synthetic/read-only cross-state parity bridge. `release_draft()` now normalizes reviewer identity into alphanumeric tokens and rejects reserved automation identities: `auto`, `automated`, `automation`, `bot`, `robot`, and `system`, including case/punctuation-separated variants. A normal named reviewer still receives a deep-copied release artifact; the staged ledger entry is not mutated.

No fixture, classification, accession, state-routing, result, hold, parity-hash, lineage, replay, provider, customer, compliance, or state-system semantics were changed.

## Exact preimages

- `infinitecal_parity.py`: Git blob `714f1abdd7e3490c837095316cfc444c513293ae`
- `test_infinitecal_parity.py`: Git blob `d6aaabb14b8b00e39114ebc6e0ab07530e099e0c`
- fixture SHA-256: `44328084e81680382eb11c9701de8b287a9cc6ec27ca613c5c33f0c926de636a`

The reconstructed local preimages matched both shipped Git blobs exactly before the repair was applied.

## Acceptance

- focused unittest: 17/17 PASS
- `py_compile` for runtime + test: PASS
- CLI frozen acceptance: 180 synthetic records = 150 `PARITY_CLEAN` + 30 HOLD (12 method-version, 9 unit/rounding, 6 duplicate-accession, 3 missing-source)
- clean parity keys: 60
- replay delta: processed/accepted/holds/drafts/events all 0
- new direct gate regressions reject `auto`, `SYSTEM`, `bot`, `Auto Reviewer`, `system.operator`, `bot_user`, `automation reviewer`, `automated-reviewer`, and `robot reviewer`
- named `QA Reviewer` remains accepted; returned release is copy-only and staged ledger state remains unchanged

## Boundaries

Synthetic/read-only only. No state/provider/customer/production write, compliance decision, outreach, automatic CoA/result release, spend, owner-PC action, reset, or force-push.