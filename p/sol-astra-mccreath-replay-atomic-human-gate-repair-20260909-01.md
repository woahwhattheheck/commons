# SOL-ASTRA-56 — McCreath replay / atomicity / human-gate repair

Operation: `mccreath-replay-atomic-human-gate-repair-20260909-01`
Source demand: `mccreath-field-sample-coa-reconciliation-lims-01`
Source PR: `#10722`
Independent review: `5158042827`

## Scope

Modified only:

- `revenue/production-lims/mccreath-field-sample-coa/field_sample_coa.py`
- `revenue/production-lims/mccreath-field-sample-coa/test_field_sample_coa.py`

New:

- `p/sol-astra-mccreath-replay-atomic-human-gate-repair-20260909-01.md`

Frozen fixture and manifest are unchanged:

- fixture Git blob `75e921c9936c2fc8bb138ca844e08c401a81f253`
- manifest Git blob `9a380cca1e006a017025096af324ecd8b768d92a`
- fixture SHA-256 `b6d732ed06587b2cf14888909888b86bf0a0ab3ac87a637990d1efcc20772a10`

Preimage on fresh main `35d76d955dc12ad164eb5dc48f602521aa15927a`:

- source blob `466fdfa00548640693e835f11981d4fc6e59172b`
- test blob `63497b56e839e71b6e678a8121a25538a64973b4`

## Repair

1. First-seen `job_id` now binds to the canonical full-job SHA-256. Exact replay remains idempotent; same ID with changed content raises `JOB_ID_PAYLOAD_MISMATCH` before any ledger mutation.
2. Clean-row accession/split/result/CoA objects are fully built and the golden result identity is validated before any per-job ledger state or events are committed.
3. The staged CoA release label gate now fails closed for non-string, blank, one-token, and normalized reserved automation/service identities, including segmented forms such as `A-I Reviewer`, `S Y S T E M Reviewer`, and `b.o.t Reviewer`. This is a label-level guard only, not identity authentication. A nonblank approval ID remains required.
4. Denied replay/release and bad-result paths have explicit zero-mutation regressions.

## Acceptance

Executed locally against the unchanged frozen fixture and manifest:

- `python test_field_sample_coa.py`: **16/16 PASS**
- `python -m py_compile field_sample_coa.py test_field_sample_coa.py`: **PASS**
- CLI `--verify`: **PASS**
- rows: 100
- READY: 75
- HOLD: 25
- hold counts: 10 / 5 / 5 / 5 unchanged
- accessions / splits / results / staged CoAs: 75 / 75 / 75 / 75
- events: 325
- exact full replay: 100/100 idempotent
- replay delta: zero for accessions, splits, results, CoAs, holds, events
- repaired deterministic ledger SHA-256: `5771700f6a1dab12a885e0dedba29fab46c2552e5ebcd923f32a66f9210994b4`

Frozen replacement content SHA-256:

- source `7c1532a0aa947cedb7906fed87d4c4ee647a693b0b4f6788363e26d9ca91c16b`
- test `170275fdee9c60cecec20ef0cd085aab0e4479b65dc3c6e531061b86763ae48d`

## Boundary

Synthetic/read-only only. No production LIMS, provider, customer, CoA send, compliance determination, outreach, spend, or owner-PC action. No automatic release. No force-push.
