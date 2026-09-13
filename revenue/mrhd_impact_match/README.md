# MRHD Impact Match Grant — Match-and-Milestone Evidence Rail

Internal reusable delivery evidence for the approved **Impact Match Grant
Match-and-Milestone Evidence Rail** sales motion.

This package is deliberately not an eligibility engine, scoring system,
reimbursement authority, applicant portal, compliance certificate, or
production integration. It reconciles buyer-approved evidence and arithmetic,
preserves immutable lineage, and emits fail-closed HOLD receipts for named
human review.

## Program contract encoded

Current MRHD Impact Match public rules used by the synthetic acceptance
configuration:

- awards: USD 25,000–250,000 for one-year projects;
- required grantee match: exactly 25% of the awarded amount;
- no more than 50% of the required match may be in-kind;
- focus areas:
  1. Economic Development / Community Improvement / Tourism
  2. Human Services / Health Services
  3. Civic / Public / Charitable / Patriotic / Religious
  4. Leisure / Cultural / Historical
  5. Education
- configured geography:
  - Iowa: Cherokee, Crawford, Ida, Monona, Plymouth, Woodbury
  - South Dakota: Union
  - Nebraska: Dakota

The rail does **not** decide whether an applicant/project is legally eligible,
whether evidence is acceptable, whether a valuation is correct, whether a
project achieved impact, or whether a reimbursement should be released.
MRHD staff / Grant Review Committee / Board retain those decisions.

## What the executable proves

`rail.py` consumes deterministic evidence events:

- `AWARD_APPROVED`
- `MATCH_COMMITMENT`
- `CONTRIBUTION_VERIFIED`
- `AMENDMENT_APPROVED`
- `PARTNER_CHANGED`
- `MILESTONE_RECORDED`
- `RETURN_RECORDED`
- `CLOSEOUT_REQUESTED`

It emits:

- one canonical award state per approved synthetic award;
- exact integer-cent 25% required-match arithmetic;
- 50%-of-required-match in-kind cap arithmetic;
- commitment vs. verified-realization separation;
- amendment, partner-change and returned-fund lineage without overwriting prior state;
- retry receipts (`replay_event_ids`) and fail-closed idempotency/sequence conflicts;
- late/partial/missed milestone review receipts;
- per-award and cycle-wide cent totals;
- a deterministic SHA-256 manifest digest and caller-keyed HMAC-SHA256 signature.

The caller owns the signing key. This package never stores or returns it.

## 180-record synthetic acceptance fixture

`fixture.py` returns **exactly 180 synthetic events**. It spans all five focus
areas and all eight configured county/state geographies and deliberately
contains:

- exact duplicate retries representing timeout-after-commit / interrupted retry;
- changed-content retry under the same event ID;
- partial/unverified match;
- verified in-kind evidence above the permitted share;
- amended award/match values;
- partner change lineage;
- late, partial and missed milestones;
- returned funds;
- unmatched contribution;
- duplicate award ID;
- unknown award;
- sequence collision;
- invalid configured geography/category;
- return-over-award and over-realized-contribution attempts.

No applicant names, beneficiary PII, production finance/grant records, or buyer
credentials are present.

## Reproduce

From repository root:

```bash
python -m unittest revenue.mrhd_impact_match.test_rail -v
python -O -m unittest revenue.mrhd_impact_match.test_rail -v
python -m py_compile \
  revenue/mrhd_impact_match/rail.py \
  revenue/mrhd_impact_match/fixture.py \
  revenue/mrhd_impact_match/test_rail.py
```

The binary acceptance target is not "no HOLDs": the hostile fixture is supposed
to prove that ambiguous/invalid evidence remains visibly held. The target is
deterministic classification, exact arithmetic, immutable lineage, zero
duplicate logical transitions on retry, and byte-identical clean-room replay.

## Authority boundary

This is internal evidence supporting a sales/delivery promise. It performs no
buyer outreach, payment action, award/reimbursement decision, production
mutation, applicant communication, or deployment. A customer-specific
delivery remains `HOLD_UNTIL_YES_AND_PAYMENT` under the existing sales lane.
