# Swarm Product-Lane Collision Preflight

Deterministic evidence compiler for **product/revenue-lane ownership collisions before a fleet TAKE**. It does not query GitHub or Slack and it never grants TAKE, outbound, merge, payment, or revenue authority.

Inputs are owner/provider-exported evidence: a candidate semantic signature (`actors`, `objects`, `actions`), declared synonym families, required provider surfaces, and one retained-root-bound search record per required provider/family pair. Any missing, rate-limited, truncated, errored, stale, future, contradictory, or root-mismatched evidence fails closed.

Results:

- `COLLISION` — at least one materially-same durable `TAKE`/`CLAIM` carrier predates or ties the candidate.
- `CLEAR_ON_SUPPLIED_EVIDENCE` — the declared census is complete/fresh and no earlier durable materially-same carrier appears.
- `UNKNOWN_HOLD` — the evidence census cannot safely establish either result.

A durable carrier is a GitHub issue/PR or Slack message explicitly labeled `TAKE` or `CLAIM`. Chatter and code-search hits can remain in provider evidence but do not establish ownership. Semantic matching is deterministic: exact operation identity, or nonempty intersection across all three normalized token families (actor + object + economic action).

## Root contract

For each search row, `retained_root` is SHA-256 of canonical JSON (sorted keys, UTF-8, no extra whitespace) over exactly:

`provider`, `family_id`, `query`, `observed_at`, `state`, `hits`.

The compiler verifies this before using the evidence.

## CLI

```bash
python -m tools.swarm_product_collision.cli compile example.json out
python -m tools.swarm_product_collision.cli verify example.json out
```

Compilation writes four create-exclusive mode-0600 leaves: `packet.json`, `review.md`, `collisions.csv`, and `receipt.json`. Verification recompiles from source evidence and requires exact bytes.

## Authority boundary

`CLEAR_ON_SUPPLIED_EVIDENCE` means only that the supplied census satisfied this contract. A seat still follows live provider-search, current-owner, Muse/outbound, repository, and merge policies. This tool performs no provider/network mutation and makes no customer, revenue, payment, savings, or legal conclusion.
