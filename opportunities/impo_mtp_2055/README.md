# IMPO MTP 2055 bid-readiness compiler

Operation: `IMPO-MTP2055-BID-READINESS-ZERN6P2-20260914`

This package turns an explicitly evidenced input into a deterministic owner-review receipt and Markdown gate packet for the Indianapolis Metropolitan Planning Organization's 2055 Metropolitan Transportation Plan RFP.

It does **not** contact IMPO, create or alter a vendor profile, register for the pre-bid meeting, sign a form, commit a price, transmit a proposal, accept a contract, or spend money. Every external authority bit is explicit and false in the shipped owner-review input.

## Why this opportunity is consequential

The official RFP states a $215,000 not-to-exceed budget, a September 16 question deadline, and an October 6 proposal deadline. The work covers a 20-24 month federally compliant MTP update with regional engagement, a statistically valid survey, performance measures, scenario/model integration, investment and project-scoring work, fiscal constraint, policy and implementation recommendations, public review, and editable final handoff. The published evaluation allocates 35 points to approach, 35 to the team, and 30 to past experience.

Those facts create a real qualification problem: a persuasive narrative is useless without a verified lead entity, UEI, named and available staff, three relevant projects and references, disclosed committed specialists, federal certifications, credible insurance posture, exact addenda, task-level price approval, and final sign/send authority. This compiler keeps those distinctions visible instead of converting missing evidence into confident prose.

## Files

- `input.owner-review.json` - truthful initial state; deliberately blocked.
- `source_requirements.json` - page-referenced source catalog; deliberately un-hashed until exact bytes are retrieved.
- `questions.json` - owner-review question queue for the published question deadline; no send authority.
- `response_architecture.md` - 16-page allocation, delivery architecture, team shape, and commercial work breakdown.
- `schema.py` - strict, detached validation with exact keys and bounded values.
- `engine.py` - deterministic requirement gates, status selection, receipt hashing, and safe Markdown rendering.
- `cli.py` - bounded no-follow reads plus create-exclusive, dirfd-relative output writes.
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

Use `--require-submission-ready` to return exit code 3 while any source, qualification, commercial, or explicit authority gate remains blocked.

## Status semantics

- `SOURCE_HOLD` - exact source generation, freshness, addenda, or deadline truth is blocked.
- `QUALIFICATION_HOLD` - required organization, team, experience, capability, or document evidence is blocked.
- `COMMERCIAL_HOLD` - task pricing, budget ceiling, or approval is blocked.
- `OWNER_REVIEW_READY` - source, qualifications, documents, and commercial evidence are ready, but explicit sign/price/send authority is absent.
- `SUBMISSION_READY` - all gates, including explicit owner authority, are ready. The compiler still does not send anything.

## Source notes

Primary source: IMPO, *Request for Proposals for Professional Services for Metropolitan Transportation Plan (MTP) 2055*, released September 9, 2026. The shipped input intentionally leaves `source_sha256` empty because the exact PDF bytes were not available inside the build runtime. That remains a hard `SOURCE_HOLD` until a reviewer retrieves and hashes the authoritative bytes.
