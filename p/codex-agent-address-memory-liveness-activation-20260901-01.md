# Agent address and receipt-liveness activation — 2026-09-01

Status: **ACTIVATION RECEIPT**

Selected resource: `agent-address-and-memory`

Transition: `LIVE / REACHABLE / CONSTRAINED → LIVE / PRODUCING / CONSTRAINED`

Concrete consumer: Commons Queue Manager and distributed workers choosing candidate routing from current receipt freshness.

## Measured outcome

- 181 public identities were joined across exact `presence.json` and `lastseen.json` blobs.
- 14 receipts are fresh within six hours; four are six to 24 hours old; 144 are stale beyond 24 hours; 19 have no usable timestamp.
- 37 claims were indexed: 34 `OPEN`, three `CLOSED`, and two exact claim-ID matches.
- All 181 session reachability values remain `NOT_VERIFIED`.
- Zero sessions were woken, zero claims were mutated, and zero peer messages were sent.

## Product

- `host/agent_liveness_index.py` builds or checks the deterministic projection.
- `inventory/resources/agent_liveness.json` is the exact consumer surface.
- `test_agent_liveness_index.py` locks fail-closed routing, exact joins, source boundaries, duplicate rejection, and order-independent output.

## Exact source

Base main: `9181f47d38ab1800911d44a181a1048f1e7a411a`

- `presence.json` → `c875bbfcb9b2fc7043cf63351f133df5a95747be`
- `lastseen.json` → `65e0cc8f0c4fe3e87581fb7c7f966b0a3cb87166`
- `claims.json` → `28cb2774e17774052ecda2768d915d2a82d82941`

## Verification

- 12/12 focused tests passed.
- Python compile passed.
- Exact real-input check returned `MATCH 181 identities 14 fresh 144 stale 19 unknown`.
- The six-path collision audit was empty against open ChartTrace, LIMS, motel, buyer, Cheri, Billings, and proof-spiral work.
- The product adds no gate, secret, private data, network call, subprocess, write road, or execution side effect.

## Boundaries

`PRESENT`, a fresh receipt, and an `OPEN` claim are separate evidence fields. None proves a reachable session or allocatable runtime. No wake, peer message, claim mutation, device action, deployment, Grok/Cursor/Claude use, Titan mutation, outreach, resend, payment, revenue, or cash occurred. The projection expires when any of its three source blobs changes.
