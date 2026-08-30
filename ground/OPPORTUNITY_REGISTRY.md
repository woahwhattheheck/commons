# Opportunity registry

Non-dilutive commercialization lane for verified public Commons technology.

Human door: [opportunity.html](../opportunity.html).
Packets: [proof-to-proposal.html](../proof-to-proposal.html).
Machine: [opportunity_registry.json](../revenue/ip/opportunity_registry.json).
Engine: [host/opportunity_registry.py](../host/opportunity_registry.py).
Seed: [opportunity_seed.json](../revenue/ip/opportunity_seed.json).

## What it is

A fail-closed registry that **composes** already-landed surfaces:

- grants ledger (`revenue/ip/grants_ledger.json`) — not reminted
- White Box collaboration offers
- collaboration targets
- distribution procurement channels
- exact receipts for TITAN Hands, RINGDELTA/Muhlnickel, carrier roads, evidence record, agent swarm, trust-cache reliability, and feature/resource trackers
- listing registry (`listing-registry.html` / `revenue/listing_registry/registry.json`) as a hashed compose source — **not reminted**. That door is offer × surface marketplace copy. This desk is funder, program, pilot, licensing, procurement, and research partnership rows.

Each row records fit, program eligibility text, applicant eligibility `UNKNOWN`, deadline freshness, exact source URLs, owner action, required artifacts, stated funding, expected value `UNKNOWN`, and a probability state. Probability is not a percentage.

## What it refuses

- Submitting applications or using funder forms
- Accepting terms
- Adjudicating applicant eligibility
- Claiming IP rights, legal status, partnerships, awards, or cash
- Inventing LICENSE terms (current main has no root LICENSE file)
- Auth, login, seats, or allowlists

`python3 host/opportunity_registry.py next` is always `NONE_READY / APPLICANT_ELIGIBILITY_UNKNOWN`.

## Commands

```text
python3 host/opportunity_registry.py compile
python3 host/opportunity_registry.py validate
python3 host/opportunity_registry.py list
python3 host/opportunity_registry.py due
python3 host/opportunity_registry.py next
python3 test_opportunity_registry.py
```

Compile is deterministic. It rewrites the public JSON, packets, `opportunity.html`, and `proof-to-proposal.html`.

Linked from [current work](../current-work.html), [distribution](./DISTRIBUTION.md), [profitability](./PROFITABILITY_BUILD_MAP.md), and [proof-to-proposal](./PROOF_TO_PROPOSAL.md).
