# MCC 1017-27 — collaborative AI workspace pursuit

Internal pursuit carrier for Metropolitan Community College-Kansas City IFB **1017-27, Cloud-Based Collaborative AI Workspace Software**.

**Current posture:** `PARTNER_FIRST / HOLD_BUYER_PACKAGE / $24,000 PROPOSED_NOT_ACCEPTED / $0 BOOKED / $0 CASH`.

This directory is not a proposal, customer-facing storefront, buyer instruction, send authority, bidder-eligibility claim, award, invoice, or revenue record.

## Why this carrier exists

Current public discovery describes an open higher-education procurement for a secure collaborative AI workspace with multi-model access, shared workspaces, custom assistants, knowledge repositories, role-based administration, analytics, privacy controls, SSO/LMS integration, implementation, training, support, and renewal pricing.

The same discovery layer reports a minimum of five years relevant enterprise/higher-education cloud AI, collaboration, or SaaS experience and at least three higher-education references. Those facts are useful for screening, but discovery indexes are **not the controlling buyer package**.

The buyer package is therefore deliberately empty in `state.json`. The package filenames presently indexed are:

- `Public Purchase - Vendor Response Instructions.docx`
- `IFB 1017-27 Pricing Form.docx`
- `1017-27 Bid Package (4) (4).docx`

Until literal buyer/buyer-portal bytes for the package, addenda, and Q&A are retained with digests, the compiler returns `HOLD_BUYER_PACKAGE`.

## Source authority

Two evidence classes are intentionally separate.

### Controlling buyer authority

Only literal buyer or buyer-portal artifacts retained in `buyer_authority.documents` may become controlling. Every retained document needs an exact SHA-256, source URL, capture time, and `authority=controlling`.

No controlling buyer bytes are retained yet.

### Secondary discovery

`state.json` records current discovery sources from Bidscope, HigherGov, and Govly. They may support opportunity discovery and questions to resolve. They may never be promoted into controlling package authority.

The secondary layer currently reports:

- solicitation 1017-27;
- posted September 14, 2026;
- questions September 25 at 17:00;
- proposal October 5 at 16:00;
- online submission through Public Purchase;
- five-year relevant-experience gate;
- three higher-education-reference gate.

The timezone and exact controlling wording for those dates remain unbound until the buyer package is retained.

## Qualification contract

`qualification.py` is a deterministic, fail-closed compiler. It enforces:

1. exact opportunity and buyer identity;
2. every discovery source remains marked `secondary`;
3. all three indexed package files are required before `package_complete=true`;
4. retained buyer files require SHA-256, HTTPS source, capture UTC, buyer/buyer-portal source kind, and controlling authority;
5. direct-prime qualification requires independently verified relevant experience of at least five years plus at least three verified higher-education references;
6. partner marketing/public case studies do **not** count as solicitation qualification;
7. a controlling proposal deadline that has passed forces HOLD;
8. every external-authority bit is structurally required to remain false;
9. commercial state remains `PROPOSED_NOT_ACCEPTED`, `$0 booked`, `$0 cash`;
10. compiled semantics receive a deterministic SHA-256 receipt.

Possible decisions are:

- `HOLD_BUYER_PACKAGE`;
- `HOLD_PRIME_QUALIFICATION`;
- `HOLD_PROPOSAL_DEADLINE_PASSED`;
- `READY_FOR_OWNER_PRIME_DECISION`.

The final state is deliberately **not** `READY_TO_SEND` or `READY_TO_SUBMIT`.

## Verification

From repository root:

```bash
python -m unittest -v test_mcc_1017_27_pursuit.py
python -O -m unittest -v test_mcc_1017_27_pursuit.py
python -m py_compile revenue/mcc_1017_27_ai_workspace/qualification.py test_mcc_1017_27_pursuit.py
python revenue/mcc_1017_27_ai_workspace/qualification.py \
  revenue/mcc_1017_27_ai_workspace/state.json \
  --now 2026-09-18T01:30:00Z
```

The current state must compile to `HOLD_BUYER_PACKAGE`.

## Partner-first posture

Current public-fit candidates are recorded in `partner_candidates.md`. Presidio, CDW, and SHI each publish higher-education/cloud/AI adjacency. That is enough to justify further qualification research, not enough to assert intent, procurement eligibility, five-year compliance, three qualifying references, platform fit, teaming permission, or interest.

No partner is selected.

## Proposed paid TJLabs workshare

`paid_workshare.md` defines a bounded **$24,000 fixed** implementation/assurance hypothesis covering requirements traceability, privacy/model-training controls, multi-model governance, knowledge-ingestion acceptance tests, SSO/LMS integration QA, eight role-specific pilot templates, telemetry/governance acceptance, enablement materials, two remote training sessions, and a deterministic pilot acceptance packet.

The workshare is not accepted and creates no receivable.

## Required next decision sequence

1. Acquire literal current Public Purchase package bytes and any addenda/Q&A.
2. Hash and retain every controlling artifact; populate exact controlling dates.
3. Re-run the compiler.
4. Verify a candidate prime's five-year experience and three higher-education references against retained evidence.
5. Bind platform/product fit to the buyer's literal requirements.
6. Resolve the questions in `question_register.md`.
7. Re-run exact tests and source review on the resulting immutable head.
8. Only after a fresh communication census and separate single-writer authorization may an owner decide whether one partner qualification message is appropriate.

No historical selection, silence, discovery note, issue, branch, test result, or this directory is external send authority.
