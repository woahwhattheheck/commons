# SOL-ASTRA — CSU malt replay/cutoff repair

Repair: `csu-malt-replay-cutoff-repair-20260909-01`
Source demand: `csu-malt-method-expansion-lims-01`
Released review blocker: GitHub review `5157213235` on merged PR #11153.

## Owned paths

- UPDATED `revenue/production-lims/csu-malt-method-expansion/csu_malt_expansion.py`
- UPDATED `revenue/production-lims/csu-malt-method-expansion/test_csu_malt_expansion.py`
- NEW `p/sol-astra-csu-malt-replay-cutoff-repair-20260909-01.md`

Fixtures, manifest, README, provider/customer systems, and all unrelated paths are unchanged.

## Reproduced defects

1. `classify()` mapped every phase other than `BEFORE_CUTOFF` to `NEXT_WEEK`, so malformed/unknown cutoff phases were silently routed.
2. `process()` returned `IDEMPOTENT_REPLAY` solely from membership in `Ledger.seen`; changed content reusing a prior `submission_id` skipped payload-identity checking. The ID was also inserted into `seen` before classification, so a classification failure could leave partial mutation.

## Repair

- `received_phase` must be exactly `BEFORE_CUTOFF` or `AFTER_CUTOFF`; unknown values raise `RECEIVED_PHASE_INVALID` before ledger mutation.
- `Ledger.submission_hashes` records the canonical full input payload hash for every first-seen submission ID.
- An exact repeated payload remains `IDEMPOTENT_REPLAY`; a changed payload under the same submission ID raises `REPLAY_PAYLOAD_MISMATCH` before mutation.
- Replay identity and sample duplicate identity remain distinct: a new submission ID for an already-accessioned sample is still `DUPLICATE_ID`.
- Held submissions follow the same rule: exact retry is idempotent, changed content under the held submission ID is rejected.

## Acceptance executed

Fresh publication baseline before blob creation:

- main `e96255f38bca533e9516144af382b2a216cee50a`
- tree `960ba17beff7fc22ba52084c4b9f612f062d8d52`
- source preimage blob `9ea2d433946b5d331e89e93a3b075b4c9558b3ac`
- test preimage blob `4668a32bdfea47736d102493e4c54216a5a92dbf`

Commands:

```text
python -B -m unittest -v test_csu_malt_expansion.py
python -m py_compile csu_malt_expansion.py test_csu_malt_expansion.py
python csu_malt_expansion.py
```

Result: 14/14 focused tests PASS; `py_compile` PASS; full CLI acceptance PASS.

Frozen truth remains unchanged:

- 80 submissions = 60 `CURRENT_WEEK` + 8 `NEXT_WEEK` + 12 exact HOLD;
- HOLDs = 4 `DUPLICATE_ID` + 4 `UNSUPPORTED_GRAIN_METHOD` + 4 `MISSING_IDENTITY_PACKAGE`;
- 68 accessions, 130 jobs, 66 staged reports, 12 holds, 80 events;
- exactly six `ASBC-PROTEIN` third-party jobs;
- `QC-BREACH-01` stages zero reports;
- whole-ledger exact replay adds zero state.

New regressions cover unknown-phase no-mutation, changed-submission replay no-mutation, held-submission exact/changed replay identity, and new-submission/same-sample duplicate namespace.

Frozen local SHA-256:

- source `c61833bc7f84eec53908d77a9030fd8f6dce354cba1cbe787bce37555f6c0ed3`
- test `3ea1ac8c623cded9fd99e3b5c444077d76427fe21ae21356a6d7a1dcd233f4b7`

Frozen local Git blob IDs:

- source `8464ab59783a695b4d868d55c761d8c736abcd18`
- test `ac2410b2bd0196486b23bef31acb67a15a95dd38`

No provider/customer/outreach/compliance determination/spend/owner-PC action and no force-push.
