# Public-Sector Integration Workshare Capture Pack

**Status: internal sales engineering / `PROPOSED_NOT_ACCEPTED`. No outbound, bid, portal, legal, payment or revenue authority.**

This carrier turns large public-sector SI procurements into bounded workshare a qualified prime can actually buy from Token Junkie Labs without pretending TJL owns the platform, certifications, government past performance, or prime contract. The reusable product has four modules: legacy-migration evidence, integration conformance, UAT evidence, and cutover/replay evidence. Thin opportunity overlays map those modules onto current solicitations.

## Commercial shapes

- **$22,500 proposed fixed fee — 3-week Workshare Evidence Sprint:** one bounded migration or integration seam, reproducible evidence harness, one UAT/cutover handoff packet, up to two agreed review/rework cycles.
- **$95,000 proposed fixed fee — Implementation Evidence Workshare:** 8–16 weeks, up to three bounded sources/interfaces, migration + integration + UAT evidence rails, cutover rehearsal/replay and weekly evidence ledger.

Both are hypotheses until a counterparty accepts them. They are not booked, earned, receivable, or cash.

## Collision-safe workflow

1. Compile the manifest with a process-selected observation time: `python -m capture_pack.cli compile data/manifest.json --as-of 2026-09-14T03:55:00Z > /tmp/pack.json`.
2. Verify the canonical packet digest: `python -m capture_pack.cli verify /tmp/pack.json`.
3. Before a target-specific packet can leave HOLD, bind exactly `opportunity_id + target_company + channel/address` and prove `relationship_checked`, `lease_acquired`, `provider_history_rechecked`, and `opportunity_facts_revalidated`. The compiler also requires its source evidence to remain fresh and the solicitation deadline to remain open at the pack observation time.
4. Digest validity alone is not authority: the target compiler re-derives the compiled pack's schema, pricing status, no-send ceiling, evidence freshness and deadline state. A caller-resealed semantically escalated packet is rejected.
5. A control-clear target reaches only `READY_FOR_OWNER_TRANSPORT_REVIEW`. It still keeps `external_send_authorized=false`; a separately authorized sender must obtain human approval of the target-specific draft and re-read provider history immediately before send.
6. Revalidate deadline, eligibility and target-company claims immediately before any proposal-facing representation. A scout fact is not buyer acceptance.

## Why the workshare is bounded

The pack deliberately sells evidence rails that can sit under a qualified prime's platform and implementation: deterministic migration reconciliation, interface contract tests, requirement-to-evidence UAT traceability, and cutover/rollback replay proof. It does **not** claim prime status, OEM partnership, M/WBE/SDVOB status, public-sector references, security clearance, government certification, buyer sign-off, go-live authority or production mutation rights.
