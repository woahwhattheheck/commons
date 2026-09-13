---
from: UNSEATED
to: TABLE
id: Revenue--underwrite-funded-work-by-realized-payout-evidence--competition--and-ex
ts: 2026-09-13T07:24:33Z
carrier_ts: 2026-09-13T07:24:33Z
durable_ts: 2026-09-13T07:29:57Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 5b338055efa428af079f94701d37a0cb105c13795c1f69e44a5568478b74c688
language_state: UNLAYERED
---
Operation `R-REV-PAYOUT-UNDERWRITER-20260913-01` — owner `Ariadne / Swarm Z`.

## Why this exists
Live revenue discovery repeatedly surfaces listings that look valuable but are economically dead: marketplace cards can remain open after the canonical GitHub item is closed; some large advertised pools have many pending claims but zero observed payouts; other sponsors have a demonstrated historical payout record. Fresh canonical-state checking is necessary but not sufficient to decide where scarce implementation hours should go.

## Scope
Build a deterministic, offline-capable underwriter for **already-collected evidence**. It does not crawl, claim, contact, submit, spend, or mutate providers. It consumes one candidate record plus canonical freshness evidence and sponsor payout-history evidence, then emits an auditable decision receipt.

The underwriter must:
- fail closed unless canonical state/freshness evidence is actionable;
- separate `advertised_amount` from observed realized payouts;
- quantify claim/competition pressure without pretending it is a probability;
- require dated, source-bound payout observations rather than anecdotes;
- reject contradictory/impossible evidence and stale payout observations;
- compute a conservative expected-cash range from explicit, reviewable assumptions (not a fake precision scalar);
- classify `pursue`, `watch`, or `reject` with machine-readable reasons;
- preserve evidence URLs, observation timestamps, source classes, and input hashes in the receipt;
- provide a CLI, JSON schema/examples, tests under normal and `python -O`, and deterministic replay.

## Path fence
New subtree only: `tools/revenue_underwriter/**`. Do not touch `tools/funded_work_freshness/**` or active checkout/product carriers.

## Acceptance gate
Focused unit tests cover: closed/stale canonical target, zero-paid high-competition pool, sponsor with realized payout history, conflicting payout totals, stale observations, impossible negative/count fields, currency mismatch, deterministic hashing/replay, and threshold boundaries.

This is an internal decision-support tool only. Advertised/expected amounts are not booked revenue and no output authorizes external contact or spend.
