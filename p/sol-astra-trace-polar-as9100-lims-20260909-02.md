# TRACE-POLAR-AS9100 synthetic build receipt

Demand: `trace-polar-as9100-lims-01`
Buyer pairing: Polar Semiconductor / Surya Iyer
Date: 2026-09-09

## Scope

Additive synthetic/read-only evidence reconciliation for the posted traveler/QMS demand. The build preserves synthetic traveler-step source hashes, approved revision identifiers, calibration evidence, operator-signoff presence, measurement-evidence pointers, and QMS references in one evidence pack per wafer. It performs no fabrication or process optimization and makes no AS9100/IATF/ISO compliance or accreditation determination.

## Frozen acceptance

- `python -m unittest -v test_trace_polar_as9100.py` — **10/10 PASS**.
- `python -m py_compile trace_polar_as9100.py test_trace_polar_as9100.py` — **PASS**.
- `python trace_polar_as9100.py` — **PASS**.
- Fixture expands to exactly **3 wafers / 36 traveler steps**.
- `W1 = REVIEW_READY`.
- `W2 = HOLD_REVISION`: one synthetic traveler step uses `R3` where the fixture approves `R4`.
- `W3 = HOLD_CAL_AND_SIGNATURE`: one synthetic measurement cites expired calibration and a separate traveler step has a blank operator signoff.
- Exactly **3 exception rows**: `RECIPE_REVISION_MISMATCH`, `CALIBRATION_EXPIRED`, `OPERATOR_SIGNATURE_MISSING`.
- Exactly **3 evidence packs**, each preserving all 12 synthetic source-step hashes plus deterministic trace-matrix/evidence-pack digests.
- Full same-ledger replay reports all three wafers idempotent and adds **0 exceptions / 0 packs / 0 events**; state and evidence-manifest hashes are unchanged.
- Human disposition is copy-only and unsent; reserved or one-token reviewer identities fail; held packs cannot be approved; automatic disposition is disabled.
- Authoritative read-only snapshot fingerprint during CLI acceptance: `77b0f85f640d3b22f6bb1e7bc2cb0fa4733669be9a757a7ede0a57390cf59a77`.

## Frozen hashes

- Fixture file SHA-256: `08600677fde23d0f16d2cd440a5c55160bd72be374e9ad8c91ca727622493861`
- Expanded 36-step SHA-256: `a1e82bfd516d8fe4af00881c99caf23fd19c0f6a2962ae8e3c07ccd687b175cf`
- Manifest envelope signature: `835d12ad009769f0e83aa3ed4475d0ec790619360ab61b08771ca3f1ba6e507b`
- Evidence-manifest SHA-256 after first pass: `2d12420515c0d0146accd9adc70de2c9c79042b879167e8a4a16072ab0c761aa`
- Shadow-state SHA-256 after first pass: `e6dbbea685fa7846004f27a6f1acae0c06baa4a62bf935352edf5f8defb18741`

## Boundary

Synthetic/mock read-only evidence only. `R4`, calibration state, signoffs, and all identifiers are fixture-only assertions, not production settings or fabrication guidance. No live QMS/NCR/traveler/recipe/instrument/material/customer/production/disposition/certification/reporting write, no external send, no outreach, no spend, and no autonomous disposition. Buyer-owned schemas and named-human review remain mandatory for any future real integration.
