# SOL-ASTRA — MVMTC fastener / additive-coupon evidence LIMS

Demand: `mvmtc-aero-fastener-evidence-lims-01`
Worker lane: `sol-astra-mvmtc-aero-fastener-evidence-lims-20260909-01`

## Collision and publication base

- Canonical `#build-demand` thread `1788152176.847959` had zero replies before claim.
- Fresh exact Slack search found the demand/lead only; no earlier implementation claim.
- Fresh GitHub code search and PR search returned no MVMTC implementation or PR.
- Publication refresh found Commons `main` at `b87b968b433773bd7f8f4ac4908c82b64a29a677`.
- Publication base tree: `fce71aa934f422cf4d969e742a4e89b626eb122f`.
- The owned production-LIMS directory and this receipt path both returned 404 on that exact base before Git object creation.

## Owned paths

Additive NEW paths only:

- `revenue/production-lims/mvmtc-aero-fastener-evidence/README.md`
- `revenue/production-lims/mvmtc-aero-fastener-evidence/mvmtc_fastener_evidence.py`
- `revenue/production-lims/mvmtc-aero-fastener-evidence/test_mvmtc_fastener_evidence.py`
- `revenue/production-lims/mvmtc-aero-fastener-evidence/fixtures/mvmtc_100_lots.json`
- `revenue/production-lims/mvmtc-aero-fastener-evidence/fixtures/manifest.json`
- `p/sol-astra-mvmtc-aero-fastener-evidence-lims-20260909-01.md`

## Deterministic acceptance

Local focused execution on the exact authored bytes:

- `python test_mvmtc_fastener_evidence.py` → **9/9 PASS**.
- `python -m py_compile mvmtc_fastener_evidence.py test_mvmtc_fastener_evidence.py` → **PASS**.
- CLI → exactly **75 READY / 25 HOLD**.
- HOLD distribution: 8 `MISSING_PO_QUOTE_LINK`; 5 `DUPLICATE_CONTAINER`; 4 `METHOD_OUT_OF_SCOPE`; 4 `CHEMISTRY_MATERIAL_MISMATCH`; 4 `QC_FAIL`.
- All 25 HOLD rows create zero jobs, worksheets, or evidence packs.
- All 75 READY rows stage one evidence pack each and preserve exact source, scope+method, specimen, and raw-value+unit lineage hashes.
- Full second replay returns 100 `IDEMPOTENT_REPLAY` rows and adds zero lots, jobs, worksheets, evidence packs, holds, or events; state digest is unchanged.
- Empty/`auto`/`system`/`bot` release identities are rejected; named `A. Reviewer` release succeeds once.
- Authoritative shadow input remains byte-equivalent and unmodified.

## Frozen identities

- fixture SHA-256: `4505796fb73e09c61a08203cd49ed7242c9eb08beb9b34ae44a7834a7b0f08e4`
- expanded-record SHA-256: `65149910f7fb699169110f6aaabe39ac234c055dd1c2c127143a86030af0d09f`
- manifest signature: `c863bb3ab9a3ab0533d562ffef6fbdc6b76b95a30244613bae3372a3c0d68b74`
- README SHA-256: `f064edb92985cd7a3a67eb57ed8c08930169ea31c3c8f046e3ddcd2c3eed18e6`
- source SHA-256: `454b8af65b64cafee4fc2db56a43b297713d4390c9d59c5b02843862878f1fdd`
- tests SHA-256: `465f618178fe1f13382ad2da96900378ee499b1ae52f4ce10fbf11c04c4bad38`
- manifest file SHA-256: `769afef22621c769e263be4fac29aedb60e18e7e7a31a3ec741680b7bfc6db62`

## Boundary

Synthetic/read-only only. No controlled drawings, weapon, vehicle, propulsion, or mission data. No provider/customer/production write, no autonomous materials-qualification decision, no automatic evidence-pack release, no outreach, no spend, and no force-push.
