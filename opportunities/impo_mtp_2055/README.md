# IMPO MTP 2055 bid-readiness compiler

Operation: `IMPO-MTP2055-BID-READINESS-ZERN6P2-20260914`

This package compiles a **non-authorizing owner-review** receipt and Markdown gate packet for the Indianapolis Metropolitan Planning Organization's 2055 Metropolitan Transportation Plan RFP. Candidate facts and evidence references are useful for structured review, but this package does not independently authenticate them and cannot mint external authority.

It does **not** contact IMPO, create or alter a vendor profile, register for the pre-bid meeting, sign a form, commit a price, transmit a proposal, accept a contract, or spend money. All external-authority bits are required to remain false; candidate JSON that attempts to set them true is rejected.

## Why this opportunity is consequential

The published RFP states a $215,000 not-to-exceed budget, a September 16 question deadline, and an October 6 proposal deadline. The work covers a 20-24 month MTP update with regional engagement, survey work, performance measures, scenario/model integration, investment and project-scoring work, fiscal constraint, policy and implementation recommendations, public review, and editable final handoff.

Those requirements create a real owner-review problem: a persuasive narrative is useless without a supported lead entity, UEI, named and available staff, relevant projects and references, committed specialists, federal-certification posture, insurance posture, source/addenda review, and task-level price reconciliation. This compiler keeps those distinctions visible without turning caller assertions into buyer-facing authority.

## Trust model

- `compile` and `verify` are the **current** public CLI path. Current compilation owns process UTC; caller-supplied `as_of` cannot backdate current readiness.
- Current receipts are short-lived and `verify` rechecks current gate dispositions before accepting them.
- Library `compile_packet` / `verify_packet` preserve explicit-time deterministic replay only and label receipts `HISTORICAL_INTEGRITY_ONLY`.
- Candidate evidence remains `CANDIDATE_ASSERTIONS_ONLY`; an owner or separate trusted evidence system must authenticate facts outside this package.
- `submission_ready` is always `false`. This owner-review carrier does not authenticate sign, price, send, contract, or spend authority.
- Input reads bind retained-file generation metadata and visible-path identity; strict JSON rejects duplicate keys and non-finite numbers.

## Files

- `input.owner-review.json` - truthful initial state; deliberately blocked.
- `source_requirements.json` - page-referenced source catalog; deliberately un-hashed until exact bytes are retrieved.
- `questions.json` - owner-review question queue for the published question deadline; no send authority.
- `response_architecture.md` - 16-page allocation, delivery architecture, team shape, and commercial work breakdown.
- `schema.py` - strict validation with exact keys and bounded values.
- `engine.py` - historical/current compiler and verifier surfaces.
- `cli.py` - process-current compile/verify, strict bounded no-follow reads, and create-exclusive dirfd-relative output writes.
- `test_engine.py` - normal and optimized hostile tests.

## Run

From repository root:

```bash
python -m opportunities.impo_mtp_2055.cli compile \
  opportunities/impo_mtp_2055/input.owner-review.json \
  --output-dir /tmp/impo-mtp2055-packet

python -m opportunities.impo_mtp_2055.cli verify \
  opportunities/impo_mtp_2055/input.owner-review.json \
  /tmp/impo-mtp2055-packet/receipt.json \
  /tmp/impo-mtp2055-packet/packet.md
```

`--require-submission-ready` deliberately returns exit code 3 for this package because owner-review analysis cannot authenticate submission authority.

## Status semantics

- `SOURCE_HOLD` - candidate source generation, freshness, addenda, or deadline review is blocked.
- `QUALIFICATION_HOLD` - required organization, team, experience, capability, or document review is blocked.
- `COMMERCIAL_HOLD` - task pricing, budget ceiling, or commercial review is blocked.
- `OWNER_REVIEW_READY` - candidate source, qualification, document, and commercial checks are reviewable; this is **not** buyer-facing or submission authority.

No `SUBMISSION_READY` state is produced by this owner-review-only carrier.

## Source notes

Primary source: IMPO, *Request for Proposals for Professional Services for Metropolitan Transportation Plan (MTP) 2055*, released September 9, 2026. The shipped input intentionally leaves `source_sha256` empty because the exact PDF bytes were not independently available to the build runtime. That remains a hard `SOURCE_HOLD` until a reviewer retrieves and hashes the authoritative bytes. Even after a digest is supplied, this package truth-labels it as a candidate assertion unless a separate trusted evidence system authenticates it.
