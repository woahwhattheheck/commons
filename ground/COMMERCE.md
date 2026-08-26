# Outcome commerce

Commons already has sellable offers, paid-action execution, outcome receipts,
customer-job schemas, settlement-state records, outreach, licensing paths, and
expert-network operations. The Outcome Commerce Bridge composes those roads. It
does not replace them.

## Economic truth

`QUOTED` is not `CHARGEABLE`. `CHARGEABLE` is not `INVOICED`.
`AUTHORIZATION` is not `SETTLEMENT`. `SETTLEMENT` is not `PAYOUT`.
`PAYOUT` is not `BANK_AVAILABLE`.

The bridge calculates contract amounts and produces deterministic statements.
It does not move money. A rail reference, invoice, outcome proof, smart-contract
event, or marketplace receipt is evidence for its named state only.

## One economic language, every existing road

Pricing is composed from fixed, subscription, usage, outcome, milestone,
take-rate, license, and sponsorship components. Base-plus-overage is a base
component plus a usage component. Prepaid credits are append-only credit events.
A marketplace is a provider listing plus a take-rate component. Productized
service, retainer, white-label, licensing, and FTE-replacement offers use the
same event and statement contract.

Every normalized listing carries a canonical source path and JSON Pointer.
That source owns the commercial terms. The adapter exists so machines can quote
and reconcile across the whole Commons without erasing a vertical's contract.

## Events and outcomes

Economic metering events are append-only and idempotent by `event_id` and
`idempotency_key`. Exact duplicates
collapse. Conflicting duplicates fail. Corrections are new reversal or
adjustment events; old events are not edited. Verified outcomes and accepted
milestones require evidence references. Failed, candidate, escalated, or merely
attempted outcomes do not become chargeable outcome events.

One event per file keeps concurrent writers off a shared ledger. A statement is
a reproducible projection over those immutable files, not a mutable balance.

The same module extends the existing DIO lifecycle with a correlated commercial
event chain: `DISCOVERED → QUALIFIED → QUOTED → FUNDED → RUNNING → SUBMITTED →
ACCEPTED → SETTLED → BANK_AVAILABLE`, with explicit rejection, expiry, refund,
and `UNKNOWN_EFFECT` branches. The last branch blocks blind retries. A provider
lookup must name the uncertain event and the same effect key before the job can
return to `RUNNING` or advance to `SUBMITTED`.

## Interfaces

- Human: `commerce.html`
- Machine catalog: `revenue/outcome_commerce/catalog.json`
- CLI: `python3 host/outcome_commerce.py`
- Replay: `python3 host/outcome_commerce.py project --events revenue/outcome_commerce/examples/commercial_events.json`
- MCP: `commons://commerce/catalog`, `commons://commerce/manifest`, and
  `commons://commerce/a2a-skills`
- A2A: an importable skills fragment exists; no A2A server endpoint is claimed
  until a real task binding is deployed
- Execution remains on the Action Pad, Bazaar, Commons MCP `fire_action`, issue,
  and direct Git roads

All of these are public open doors. Pricing and outcome metadata describe work;
they never become identity, admission, permission, approval, login, or capability
gates.
