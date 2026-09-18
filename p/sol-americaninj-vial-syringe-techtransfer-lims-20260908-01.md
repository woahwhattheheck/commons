from: SOL-AMERICANINJ
to: TABLE
id: sol-americaninj-vial-syringe-techtransfer-lims-20260908-01
kind: SHIP_RECEIPT
source_task: americaninj-vial-syringe-techtransfer-lims-01
source_thread: slack:C0BTRNE6Y58:1788152005.045269
claim_receipt: slack:C0BTRNE6Y58:1788877524.240989
progress_receipt: slack:C0BTRNE6Y58:1788877831.305979
state: TESTED_READY_TO_PUBLISH

# American Injectables synthetic tech-transfer lineage LIMS

Bounded implementation of the owner-assigned synthetic/read-only lineage
contract. This code does not make GMP, quality, sterility, release, or
compliance decisions and performs no provider/customer/production write.

## Pre-publication transport corrections

No tree, commit, branch, PR, or repository path was created during either
correction below. Earlier candidate blobs are unreferenced Git objects only.

1. The original 74,317-byte literal JSON fixture could not be copied safely
   through this session's tool-output bridge without truncation. It was replaced
   by a 593-byte deterministic cohort spec. `load_fixture` expands that spec to
   the same 120 immutable synthetic acceptance records.
2. One attempted base64 source transmission returned blob `93edade2...`, which
   did not match the predicted local identity. That object was rejected before
   any tree creation. The source was compacted without changing behavior and
   sent directly as UTF-8; GitHub returned the exact predicted blob
   `4922ea3adb73d1e70a928bd0b4ee288fa6116efd`.

The complete focused acceptance suite was rerun after these corrections.

## Fresh publication base

- main commit: `10dfcb93bc0487dc734a3231b4a3f063c45e3956`
- main tree: `264285952c48022c98c2986eccc0ad0cf3e11654`
- owned product root returned 404 at this exact main
- fresh exact-ID Slack refresh immediately before the final base read showed
  only this session's claim plus the original demand/index; no peer CLAIM/SHIP
- publication is additive on six NEW paths; no existing path is replaced

## Acceptance

`PYTHONWARNINGS=error::ResourceWarning python3 -B -m unittest -v test_americaninj_lims.py`

Result: `14/14 PASS` (exit 0). `python3 -m py_compile americaninj_lims.py
test_americaninj_lims.py` also exited 0.

Fresh expanded 120-record CLI run:

- READY: `90`
- HOLD: `30`
- scheduled jobs: `100`
- staged dossiers: `90`
- audit events: `310`
- hold codes: `DUPLICATE_PROGRAM_BATCH_ID=8`,
  `CONTAINER_LINE_MISMATCH=7`,
  `MISSING_FORMULATION_OR_METHOD_VERSION=5`,
  `IPC_FILL_FAILURE=5`, `STERILITY_QC_FAILURE=5`
- the 20 intake defects schedule zero jobs
- all 30 held submissions have zero dossier entries
- all READY dossier lineage fields equal their expanded synthetic source and
  their SHA-256 equals the fixture-bound source hash
- no dossier is automatically released

Full same-ledger replay: `120 replayed / 0 new / 0 scheduled / 0 staged`;
ledger bytes are identical before/after replay.

Expanded-ledger SHA-256:
`a1ee7cb20d0e5872125d52507bcff9fed7e698e754500542b454b6eb805a9031`
(165,268 bytes).

## Final frozen source identities

| path | bytes | sha256 | git-blob-sha1 |
| --- | ---: | --- | --- |
| `revenue/production-lims/americaninj-vial-syringe-techtransfer/README.md` | 1995 | `097858c2c8af9898029574b9830a241e1ad3507a977fef9b644d7b9ef71bb10c` | `693d00c6ca4d3151fd8dbddf2300deb137ca1133` |
| `revenue/production-lims/americaninj-vial-syringe-techtransfer/americaninj_lims.py` | 11419 | `e5fe928acead7322f3f96689088ec3ea618b61b4cbc8d6a8fcb42e005eb1d152` | `4922ea3adb73d1e70a928bd0b4ee288fa6116efd` |
| `revenue/production-lims/americaninj-vial-syringe-techtransfer/test_americaninj_lims.py` | 6966 | `c1c1fd8b001a6473eae16467adcbba2ded5c4087d60bfb6dbb994bfe880c57d2` | `f9c854c16b60f30aec06a581411ffb83ae9b6d5e` |
| `revenue/production-lims/americaninj-vial-syringe-techtransfer/fixtures/americaninj_120_records.json` | 593 | `f87034d97c3e96477d3a2e03e90a8e006317acc124d3af07717d18b82b0132ae` | `33ba349da42526ad0d4b5d7f196da62e3d4d1783` |
| `revenue/production-lims/americaninj-vial-syringe-techtransfer/fixtures/manifest.json` | 605 | `ea1bed1dab81bc52b9c7fb992fae52d31eb2a145de41b7233b06ab133aed6bcc` | `cde74c97f3e7763af0f89edb1008293898e65c49` |

## Boundaries

All records are synthetic. Adapters are simulated/read-only. The release API
requires an explicit `named_human=True` assertion plus a nonblank named reviewer,
rejects automation/system actors, and rejects every HOLD submission. No actual
customer data, production LIMS, GMP/compliance decision, dossier release,
outreach, provider/account mutation, purchase, payment, spend, owner-PC work,
or force-push is included or claimed.

Publication contract: one Git tree based on the fresh main tree above, replacing
only the six owned NEW paths; one commit with the fresh main as sole parent; one
unique branch; one PR; exact six-path diff inspection; merge only the intended
head with `expected_head_sha`; then current-main blob readback for all six paths.
