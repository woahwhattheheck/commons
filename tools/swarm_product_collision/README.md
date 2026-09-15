# Swarm Product-Lane Collision Preflight

Deterministic evidence compiler for **product/revenue-lane ownership collisions before a fleet TAKE**. It does not query GitHub or Slack and it never grants TAKE, outbound, merge, payment, or revenue authority.

Inputs are owner/provider-exported evidence: a candidate semantic signature (`actors`, `objects`, `actions`), candidate-anchored synonym families, and one retained-root-bound search record per **code-owned required provider/family pair**. The provider universe is fixed to `GITHUB_ISSUES`, `GITHUB_PRS`, `GITHUB_CODE`, and `SLACK`; callers cannot shrink it. Any missing, rate-limited, truncated, errored, stale, future, contradictory, or root-mismatched evidence fails closed.

Results:

- `COLLISION` — at least one materially-same durable `TAKE`/`CLAIM` carrier predates or ties the candidate.
- `CLEAR_ON_SUPPLIED_EVIDENCE` — the full code-owned provider census is complete/fresh and no earlier durable materially-same carrier appears.
- `UNKNOWN_HOLD` — the evidence census cannot safely establish either result.

A durable carrier is a GitHub issue/PR or Slack message explicitly labeled `TAKE` or `CLAIM`. Chatter and code-search hits can remain in provider evidence but do not establish ownership.

## Semantic-family contract

The family layer is now mechanically bound instead of decorative:

- every candidate signature token must be the unique anchor of exactly one declared family;
- every family must anchor exactly one candidate signature token;
- a synonym term cannot belong to multiple families;
- every provider search for a family must lexically contain **every** declared family term;
- semantic matching canonicalizes candidate and hit signature tokens through those declared families, so declared synonyms actually match.

Deleting an anchored family, reminting an unrelated `COMPLETE` query, or presenting an ambiguous family is rejected before a CLEAR can be produced.

## Time contract

`search.observed_at` cannot be future-dated. A hit created after `evaluation_time`, or after the search that supposedly observed it, yields `UNKNOWN_HOLD`; it is never treated as a harmless later duplicate. A legitimate later duplicate may still be reported when it postdates the candidate but predates the provider observation and evaluation.

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
