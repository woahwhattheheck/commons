# Outreach Qualification Firewall

A deterministic, fail-closed pre-send gate for Token Junkie Labs revenue outreach.

This package exists because **a commercially interesting opportunity is not the same thing as a send-ready opportunity**. Before an outbound action reaches a prospect, partner, sponsor, maintainer, or buyer, the firewall requires retained evidence for the opportunity, adequate deadline runway, a proven response route, qualification/registration facts, a bounded paid TJLabs seam, an open relationship state, deduplication, owner review, and a single-writer lease bound to the exact action.

The code **never sends anything**.

## Decision model

There are two deliberately different outputs:

- `qualified_for_owner_review`: the retained facts are complete enough for a human owner to decide whether the exact outreach action should proceed.
- `authorized_to_send`: the qualification still passes *and* a current owner approval and current single-writer lease both bind the exact qualification and action digests.

A packet may therefore be commercially qualified while remaining unauthorized to send. That is the normal state before owner review / Muse arbitration.

## Trust boundary

The evaluator requires four independently supplied things:

1. a JSON qualification packet;
2. the retained controlling-source bytes;
3. an evaluator-supplied canonical UTC `--now`;
4. the executing writer identity.

The packet's `source.sha256` must match the retained bytes. `as_of_utc` must exactly equal the evaluator-supplied `--now`; callers cannot regain deadline runway by changing only the packet clock.

The evaluator derives:

- `qualification_digest`: exact canonical qualification facts;
- `dedupe_key`: normalized opportunity + organization + contact + route + purpose identity;
- `action_digest`: the exact qualification digest + dedupe key + action.

Owner approval binds `qualification_digest`. A writer lease binds `action_digest` and an exact `selected_writer`. Changing the target, content hash, route, economics, evidence, clock, deadline, or qualification facts after review invalidates the authorization.

## Required packet facts

- `source`: retained locator + SHA-256.
- `as_of_utc`: canonical whole-second UTC `Z`, equal to evaluator `--now`.
- `opportunity`: stable ID, absolute deadline, integer minimum runway hours.
- `submission`: route kind/locator, route proof state, registration requirement and registration state.
- `eligibility.gates`: explicit named gates. `UNKNOWN` and `FAILED` never pass. A `PROVEN` gate must contain at least one evidence reference.
- `economics`: `FIXED_FEE`, `HOURLY`, or `BOUNTY`; finite positive amount, uppercase currency, bounded scope, and a proven payment path.
- `target`: organization, contact, and relationship state. `DNR`, `BOUNCE`, `BLOCKED`, and `CLOSED` are hard stops.
- `action`: transport kind, exact route, purpose, and content SHA-256.
- `prior_actions`: dedupe receipts; a materially identical `PENDING`, `SENT`, `DELIVERED`, `ACCEPTED`, or `PAID` action blocks another send.
- optional `owner_review`: approval/rejection bound to the current `qualification_digest`, with explicit validity interval.
- optional `writer_lease`: `SELECTED`/`HOLD`/`COLLISION`/`VOID`, exact writer, exact `action_digest`, and explicit validity interval.

For email, the exact contact and action route must match after normalization. Case and `mailto:` aliases collapse to one dedupe identity.

## CLI

```bash
python p/outreach-qualification-firewall/firewall.py \
  p/outreach-qualification-firewall/fixtures/qualified_owner_review.json \
  --source p/outreach-qualification-firewall/fixtures/source_authority.json \
  --now 2026-09-17T19:00:00Z \
  --writer Z-Palisade-1445
```

Exit status is `0` only when `authorized_to_send=true`. A packet that merely qualifies for owner review exits `2`, making accidental automation fail closed.

The shipped `qualified_owner_review.json` fixture is intentionally fully qualified but has no owner review or writer lease, so it must **not** authorize outbound transport. `held_short_runway.json` is superficially attractive but fails the minimum-runway gate.

## Proof

Run:

```bash
python p/outreach-qualification-firewall/test_firewall.py
python -O p/outreach-qualification-firewall/test_firewall.py
```

The suite covers mutable-clock replay and deadline boundaries; unknown/failed qualification and missing proof references; missing/unknown response route and registration; DNR/bounce/closed relationships; zero/non-finite economics and unknown payment path; retained-source byte tampering; normalized email aliases and duplicate prior actions; stale owner approval after semantic mutation; stale/foreign/expired writer lease; exact action-content mutation after review; malformed transport and target/route mismatch; and CLI non-zero behavior for owner-review-only packets.

## Truth ceiling

This is deterministic decision-support and a pre-send safety/revenue-quality gate. It does **not** prove a buyer will respond, that a bidder/partner is qualified beyond retained evidence, that a solicitation is still authoritative, that a proposal was submitted, that an engagement exists, or that any award, payment, or revenue occurred. It never contacts anyone and never substitutes for owner review or Muse/single-writer arbitration.
