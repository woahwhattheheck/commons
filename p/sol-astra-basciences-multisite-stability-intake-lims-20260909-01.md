# SOL-ASTRA BA Sciences multi-site stability intake receipt

Demand: `basciences-multisite-stability-intake-lims-01`
Buyer pair: BA Sciences / Tim Mercier
Date: 2026-09-09

## Scope

A bounded synthetic/deidentified read-only intake shadow for the posted Micro, Chemistry, Water, and Stability form workflow. It normalizes quote/PO/specification and handling/storage fields with document provenance, routes synthetic site/method identifiers, stages exact result/report cardinality, and generates deterministic Stability pull schedules. No production interface or compliance disposition is represented.

## Frozen acceptance

- 220 deterministic signed synthetic intake records.
- 180 READY / 40 HOLD before testing.
- HOLD allocation: 7 expired quote, 7 quote/PO conflict, 7 missing controlled/storage data, 7 absent specification, 6 ambiguous result mapping, 6 incorrect Stability totals.
- READY: 180 accessions, 180 staged-not-run jobs, exact route and result cardinality, 180 staged unsent reports.
- Valid form distribution: 45 each Micro/Chemistry/Water/Stability; expected synthetic result total 495.
- Stability: 45 schedules / 180 pull events at exact 0/30/90/180-day offsets, two synthetic units each.
- Every normalized field retains source document SHA-256 and source coordinate.
- HOLD rows create zero accession/job/result/report/pull state.
- Same-ledger full replay = 220 idempotent records, zero additions, stable state digest.
- Changed-content same record ID fails before mutation.
- Named-human release is copy-only/unsent; segmented reserved actor labels fail closed; automatic release disabled.
- Fixture/manifest/document tamper and sensitive-shaped fields fail closed.

## Boundary

Synthetic/deidentified + simulated/read-only only. Synthetic site/method route identifiers are fixture assertions pending buyer/vendor golden validation. No production/provider/customer write, controlled-substance decision, compliance/regulatory disposition, report send, outreach/demo, payment/spend, owner-PC action, or force-push.

## Executed evidence on frozen product bytes

- `PYTHONWARNINGS=error::ResourceWarning python -m unittest -v test_basciences_stability_intake.py` — **13/13 PASS**, 0 failures/errors/skips.
- `python -m py_compile basciences_stability_intake.py test_basciences_stability_intake.py` — **PASS**.
- `python basciences_stability_intake.py` — **PASS** with state digest `c42c70891ba0eeb1dd2cb9603e4e4acc01a5f690c8275579d427d15e2accb8cf`.
- Fixture SHA-256 `5142a8d96ac9ef86debaca9a1beae331714cb1fa38db807f6dc79367b2aa6e43`.
- Expanded 220-record SHA-256 `8bae37596dd6fd246a2f3b6cc84e87b299afe9ff6ba6c920c1423e845d29f62c`.
- Manifest signature `447916eb60e1e74a8c35968464864b9b836417e77ae42eeeb251085b1631d6e7`.
- Product source SHA-256 `b856975a2d637c078a249a21cf292a901b0e4f2f024ef53d1737c33b6638d086`; focused test SHA-256 `1ff7280dd97d97e9bf2c9b8407b4dd963bdea360159aabcb48b7176c36643fd2`.

Publication identifiers stay in the authoritative GitHub/Slack terminal receipt rather than recursively editing this source receipt after merge.
