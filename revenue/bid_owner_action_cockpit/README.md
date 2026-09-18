# Bid Owner Action Cockpit

Offline, evidence-bound decision support for the human-only actions that remain after proposal, competition, grant, or procurement packages have already identified their blockers.

This product answers a narrow question:

> Across the live opportunities we already understand, which owner action is actually timely now, which opportunities does it affect, and which apparently similar requirements must remain separate?

It does **not** write proposals, discover solicitation requirements, contact buyers, create accounts, sign forms, submit bids, make commitments, or recognize revenue.

## Why this exists

A mature bid packet frequently ends in a small set of real-world gates: a portal account, current legal-entity facts, buyer-specific tax/vendor forms, financial evidence, an authorized signature, a named partner/site/reference commitment, pricing or insurance approval, cost share, or final submission authority.

Those gates are often repeated across multiple opportunities. Treating every occurrence as unrelated wastes owner attention; treating similar-looking requirements as interchangeable is worse. The cockpit therefore aggregates only an **exact requirement identity**:

`action_key + requirement_sha256 + generation + category`

The same action label with a different buyer requirement digest or generation remains a separate row and carries `INCOMPATIBLE_ACTION_VARIANTS_EXIST`.

A `PROVEN` gate in one opportunity never cures a `MISSING` gate in another. Buyer-specific carriers remain authoritative for their own requirement status.

## Input contract

The compiler accepts one strict JSON blocker snapshot:

- `schema_version`
- `snapshot_id`
- `opportunities[]`

Each opportunity binds:

- opaque opportunity id and owner ref;
- route state: `PRIME | TEAMING | PARTNER_REQUIRED | HOLD | NO_BID`;
- optional exact UTC response deadline;
- one source packet id, digest, capture time, and completeness flag;
- zero or more gates.

Each gate binds:

- stable gate id;
- semantic `action_key` and bounded owner-safe `action_label`;
- buyer requirement SHA-256 and generation;
- category;
- status;
- `blocking` and `owner_required` booleans;
- exact evidence refs/digests;
- same-opportunity prerequisite gate ids.

Categories are:

`PORTAL | LEGAL | FINANCE | TAX | SIGNATURE | TEAM | PARTNER | SITE | COST_SHARE | PRICING | INSURANCE | REFERENCE | SUBMISSION | OTHER`

Statuses are:

`PROVEN | MISSING | HOLD | PENDING_EXTERNAL | NOT_APPLICABLE`

The parser rejects duplicate JSON keys and IDs, unknown fields, bool-as-int aliases, malformed digests/UTC, future source captures, missing prerequisites, dependency cycles, changed exact action identity labels, and unsupported states.

## Source/currentness boundary

Policy defines a maximum blocker-packet age plus critical/high deadline windows.

If an opportunity's blocker packet is incomplete or stale, the compiler emits `SOURCE_REFRESH_REQUIRED` and suppresses its downstream gate rows. Stale or partial source evidence cannot keep an old owner action looking current.

`NO_BID` and expired opportunities become `TERMINAL`; their old blockers no longer pollute the live owner queue.

## Queue states

Every emitted row has one conservative state:

- `OWNER_ACTION_NOW` — a current missing gate explicitly requires the owner;
- `OWNER_PREP_REQUIRED` — current missing evidence/work is not an external wait and is not marked owner-only;
- `WAIT_EXTERNAL` — a current gate is awaiting outside evidence/action;
- `SOURCE_REFRESH_REQUIRED` — the authoritative blocker packet itself is incomplete or stale;
- `DEPENDENCY_BLOCKED` — a missing gate depends on another not-yet-proven gate;
- `HOLD` — the authoritative carrier explicitly says the gate is held;
- `NO_ACTION_PROVEN` — the gate is proven or not applicable;
- `TERMINAL` — the opportunity is no-bid or its controlling deadline has passed.

These are owner-review states only. They grant no external authority.

## Priority

Priority is deterministic, not an LLM score.

The queue uses:

1. source/currentness failures when they threaten a live deadline;
2. exact controlling deadline proximity;
3. number of distinct live opportunities affected by one exact requirement;
4. number of blocking gates represented;
5. stable IDs for deterministic tie-breaking.

Bands are `CRITICAL | HIGH | NORMAL | HOLD | TERMINAL`.

There is deliberately no win probability, expected-value guess, invented opportunity budget, booked-revenue field, or buyer-intent score.

## Exact unblock ledger

Each action row exposes:

- affected opportunity IDs;
- exact gate IDs;
- requirement digest + generation;
- current evidence refs/digests;
- prerequisite gate IDs;
- source packet IDs;
- blocking gate count;
- earliest controlling deadline and minutes remaining;
- deterministic reason codes.

A category projection gives the owner a second view over portal, legal, finance, tax, signature, partner, site, pricing, insurance, reference, submission, and other work without collapsing incompatible buyer requirements.

## Integrity and current verification

The compiler emits canonical JSON, a deterministic Markdown projection, a normalized-input digest, and a SHA-256 receipt.

The verifier does two checks:

1. exact historical reconstruction at the retained `evaluated_at` proves the packet was not tampered with or resealed against different inputs/policy;
2. a fresh compile at trusted process time must preserve the action state/priority/reason semantics.

A formerly current packet therefore stops verifying when its source becomes stale, a deadline expires, or a deadline-priority boundary is crossed.

Library callers may provide an explicit time for deterministic testing/replay. Production CLI commands sample process UTC internally; there is no caller `--now` / `--as-of` current-authority override.

## CLI

Compile:

```bash
python -m revenue.bid_owner_action_cockpit compile \
  --input blocker_snapshot.json \
  --policy owner_action_policy.json \
  --output cockpit.json \
  --markdown cockpit.md
```

Verify current semantics:

```bash
python -m revenue.bid_owner_action_cockpit verify \
  --input blocker_snapshot.json \
  --policy owner_action_policy.json \
  --output cockpit.json
```

Render Markdown only after current verification:

```bash
python -m revenue.bid_owner_action_cockpit render \
  --input blocker_snapshot.json \
  --policy owner_action_policy.json \
  --output cockpit.json \
  --markdown cockpit.md
```

CLI input is bounded regular-file input with no-follow protection where available. Outputs are create-exclusive ordinary files; pre-existing paths and symlink targets are refused.

## Synthetic portfolio proof

`example_input.json` contains eight opportunities demonstrating:

- one exact legal-entity requirement shared by three live opportunities;
- two same-label tax/vendor requirements with different buyer digests that stay separate;
- a pending external partner gate;
- a financial-evidence -> signature dependency chain;
- a proven reference gate;
- an incomplete source packet;
- a `NO_BID` opportunity;
- an expired opportunity.

At replay time `2026-09-14T01:30:00Z` with `example_policy.json`, the frozen receipt is:

`a5bc6e56fae6c001f6af34b3a6276ed9b7f9eb67bc283b7bff91785926596e96`

Expected summary: 8 opportunities, 10 queue rows, 4 `OWNER_ACTION_NOW`, 1 source refresh, 2 terminal opportunities, 5 affected live opportunities. `source:zeta` is first because incomplete source truth threatens the nearest live deadline.

## Tests

```bash
python -m py_compile \
  revenue/bid_owner_action_cockpit/core.py \
  revenue/bid_owner_action_cockpit/cli.py \
  revenue/bid_owner_action_cockpit/test_core.py \
  revenue/bid_owner_action_cockpit/test_cli.py \
  revenue/bid_owner_action_cockpit/test_fixture.py

python -m unittest \
  revenue.bid_owner_action_cockpit.test_core \
  revenue.bid_owner_action_cockpit.test_cli \
  revenue.bid_owner_action_cockpit.test_fixture

python -O -m unittest \
  revenue.bid_owner_action_cockpit.test_core \
  revenue.bid_owner_action_cockpit.test_cli \
  revenue.bid_owner_action_cockpit.test_fixture
```

The focused suite contains 43 tests across aggregation, source freshness/completeness, exact requirement identity, incompatible variants, dependency closure, terminal routing, deterministic priority, receipt/current verification, golden fixture behavior, and filesystem publication refusal.

## Authority ceiling

This is internal owner decision support only. Neither `OWNER_ACTION_NOW` nor any other state authorizes or performs:

- W-9/EIN/tax-form creation or taxpayer representations;
- financial statement creation, accounting attestations, bank data, or audit assertions;
- signatures, certifications, insurance attestations, references, partner/site commitments;
- portal/account creation or registration;
- pricing, cost-share, staffing, legal, or contractual commitments;
- buyer/partner/sponsor contact;
- proposal/bid/grant/competition submission;
- contract acceptance, spend, payment, award, cash assertion, or revenue recognition.

The authoritative buyer-specific carrier still determines what evidence is required and whether its gate is actually proven. The cockpit only reconciles that evidence into a deterministic human-action queue.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)
