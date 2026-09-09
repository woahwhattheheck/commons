# SARA partner eDNA/qPCR accession build receipt

Demand: `sara-partner-edna-accession-lims-01`
Buyer pairing: San Antonio River Authority Regional Environmental Laboratory / Shannon Tollison
Date: 2026-09-09

## Scope

Additive synthetic/read-only partner accession shadow. It reconciles partner/client COC and container identity, routes only known matrix/analyte pairs to pinned scope/panel/method versions, binds qPCR control batches, stages unsent QA reports, and preserves provenance digests. It does not make a public-health, regulatory, accreditation, compliance, diagnostic, or release decision.

## Frozen acceptance

- `python -m unittest -v test_sara_partner_accession.py` — **10/10 PASS**.
- `python -m py_compile sara_partner_accession.py test_sara_partner_accession.py` — **PASS**.
- `python sara_partner_accession.py` — **PASS**.
- 240 expanded synthetic/deidentified submissions: exactly **192 READY / 48 HOLD**.
- Holds: exactly 8 each `MISSING_SUBMITTER_OR_CUSTODY`, `MATRIX_ANALYTE_MISMATCH`, `DUPLICATE_ID`, `HOLD_TIME_BREACH`, `PARTNER_CLIENT_IDENTITY_MISMATCH`, `QPCR_CONTROL_FAIL`.
- Two four-record failed qPCR control batches hold all eight represented members; only one seeded control row per batch is false.
- READY creates exactly 192 accessions, 192 jobs and 192 unsent `STAGED_HUMAN_QA` reports; held rows create zero job/report state.
- Full same-ledger replay reports 240 idempotent replays and adds zero accessions/jobs/reports/holds/events; state digest remains `7e205f05c72a83560d87058d980a5cd0432249e97bdc5368308a40c5e044c903`.
- Named-human release is copy-only and unsent; reserved/one-token identities fail; automatic release is disabled.
- Authoritative read-only shadow fingerprint during acceptance: `ea049b39b7da60efcebfe2a47775857212950f0df7fb73d80a6238d6e9e183b8`.

## Frozen hashes

- Fixture file SHA-256: `fb83ca92f802aa65361c713b8b82054dd7b43af26e284d62d2fbc5e4b891ad84`
- Expanded 240-record SHA-256: `1c0c89378a808a5e22a1a0adffe7d211d398fa05a875a2574f85a9efa89bc3b3`
- Manifest envelope signature: `eeb31d58f195cb5413fad5882d310a02cf9796a5038d80588d49179e6d4331c3`

The manifest additionally pins the facility, program/client map, route table, 4-record control-batch size, exact counts, and hold distribution. Fixture/manifest tamper tests fail closed.

## Boundary

Synthetic/deidentified fixtures only. Simulated/read-only adapter shape only. No production/state/provider/customer write, external send, outreach, spend, automatic release, real regulatory decision, or owner-PC action. Real schemas/golden round trips remain buyer/vendor-owned future integration work.
