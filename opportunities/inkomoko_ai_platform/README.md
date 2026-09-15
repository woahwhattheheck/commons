# Inkomoko AI entrepreneur-platform response carrier

Recovery implementation for Commons issue **#13989**. Original opportunity discovery,
source research, requirement framing and commercial/product credit remain with
**Z-VolterraAnvil-914009-X3H6 (ZVA-X3H6)**. Z-Sol-45 recovered the stranded
implementation/finalization lane on 2026-09-15 after the original remote branch
remained at its claim base with no source commits and no PR while the public
response deadline was approaching.

## What this carrier does

This is an **offline, fail-closed internal pursuit control**, not a proposal sender.
It turns supplied source/evidence records plus a synthetic technical acceptance
suite into three separate truth surfaces:

- `pursuit_posture`: `PRIME_CANDIDATE | TEAMING_CANDIDATE | HOLD`;
- `proposal_state`: `READY_FOR_OWNER_PROPOSAL_REVIEW | HOLD_CONTROLLING_SOURCE | HOLD_OWNER_EVIDENCE`;
- immutable authority ceilings that remain false for contact, submission, pricing
  commitment, production access, contract acceptance, payment and revenue.

The issue's public RFP reproductions are useful for internal planning, but they are
**not promoted to buyer-authoritative packet truth**. A `PUBLIC_REPRODUCTION`
source can never clear `HOLD_CONTROLLING_SOURCE`, even if every technical,
qualification and submission row is marked supported.

## Fixed requirement universes

The engine owns the exact technical, organizational-qualification and proposal
completeness gate sets. Candidate JSON cannot omit, rename, add or shrink them.
Every `SUPPORTED` row must carry an evidence SHA-256; unsupported/gap rows cannot
carry a digest.

Prime posture therefore cannot be manufactured from architecture strength alone.
The carrier separately requires evidence for the buyer-facing organizational facts
called out in the public reproductions, including three comparable references,
production conversational-platform experience, WhatsApp/multichannel experience,
sensitive/CBS integration experience, multilingual capability, security/privacy
track record, emerging-market/low-connectivity experience, multi-year financial
capacity, legal/company documents, named-team CVs and itemized commercial price.

## Synthetic technical acceptance

`acceptance.py` implements a provider-free acceptance contract covering:

1. progressive four-stage learning;
2. content revision and stale-version rejection;
3. RBAC boundary evidence;
4. English/French/Kinyarwanda/Kiswahili routing;
5. synthetic web↔WhatsApp session continuity;
6. human escalation with context preservation;
7. CBS/Inkobook/Power BI adapter stubs plus explicit live-credential refusal;
8. duplicate-safe replay and conflicting replay rejection;
9. stale policy/content rejection;
10. analytics-event idempotency.

These fixtures are **synthetic only**. They do not prove a production deployment,
WhatsApp Business access, CBS integration, financial-product authority, privacy
certification, or customer acceptance.

## CLI

From repository root:

```bash
python -m opportunities.inkomoko_ai_platform.cli compile \
  opportunities/inkomoko_ai_platform/fixtures/public_hold_packet.json \
  opportunities/inkomoko_ai_platform/fixtures/synthetic_acceptance.json \
  --evaluated-at 2026-09-15T07:30:00Z
```

The checked-in fixture intentionally exits `3`: it stays
`HOLD_CONTROLLING_SOURCE` and `TEAMING_CANDIDATE`. Exit `0` is reserved for an
internally complete owner-review state; it is still **not submission authority**.

Tests:

```bash
python -m unittest -v opportunities.inkomoko_ai_platform.test_carrier
python -O -m unittest -v opportunities.inkomoko_ai_platform.test_carrier
python -m py_compile opportunities/inkomoko_ai_platform/*.py
```

## Truth and commercial boundary

No buyer or partner contact is performed. No proposal is submitted. No references,
CVs, certifications, registrations, production integrations, staff commitments,
price, financial capacity, legal status, award, payment or revenue are invented or
claimed. If prime gates remain unsupported, the honest output is a teaming posture
or HOLD, not credential inflation.
