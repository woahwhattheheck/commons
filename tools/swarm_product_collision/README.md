# Swarm Product-Lane Collision Preflight

Deterministic evidence compiler for **product/revenue-lane ownership collisions before a fleet TAKE**. It does not query GitHub or Slack and it never grants TAKE, outbound, merge, payment, or revenue authority.

Inputs are owner/provider-exported evidence: a candidate semantic signature (`actors`, `objects`, `actions`), candidate-anchored synonym families, and retained-root-bound provider search records over the **code-owned provider universe** `GITHUB_ISSUES`, `GITHUB_PRS`, `GITHUB_CODE`, and `SLACK`. Callers cannot shrink that provider universe.

Results:

- `COLLISION` — at least one materially-same durable `TAKE`/`CLAIM` carrier predates or ties the candidate.
- `CLEAR_ON_SUPPLIED_EVIDENCE` — every required provider/family/term search is complete/fresh and no earlier durable materially-same carrier appears.
- `UNKNOWN_HOLD` — the evidence census cannot safely establish either result.

A durable carrier is a GitHub issue/PR or Slack message explicitly labeled `TAKE` or `CLAIM`. Chatter and code-search hits can remain in provider evidence but do not establish ownership.

## Semantic-family contract

The family layer is mechanically bound:

- every candidate signature token is the unique anchor of exactly one declared family;
- every family anchors exactly one candidate signature token;
- a synonym term cannot belong to multiple families;
- declared synonym terms canonicalize to the same family during semantic matching;
- every declared synonym term must have its **own exact search row for every required provider**.

The final point is deliberate. A single space-joined query such as `franchise-owner franchisee` is not accepted as proof for both synonyms because common provider search syntax interprets space-separated terms as an intersection and can miss a carrier that uses only one synonym. Each row's `query` must therefore equal exactly one declared family term. Extra query text, provider modifiers, negative terms, repository/channel filters, and other caller-supplied scope narrowing are rejected.

Example required rows for a family `["franchise-owner", "franchisee"]`:

- `GITHUB_ISSUES` × `franchise-owner`
- `GITHUB_ISSUES` × `franchisee`
- `GITHUB_PRS` × both terms separately
- `GITHUB_CODE` × both terms separately
- `SLACK` × both terms separately

Missing any required provider/family/term row yields `UNKNOWN_HOLD`.

The declared family vocabulary is still owner-supplied evidence: the compiler does not invent undisclosed synonyms or perform fuzzy inference. `CLEAR_ON_SUPPLIED_EVIDENCE` is intentionally limited to the declared vocabulary and the supplied provider evidence.

## Provider-evidence consistency

Each search row is retained-root-bound to its exact provider, family, query term, observation time, state, and hits.

A `hit_id` is reconciled **globally before durable/semantic filtering**. If the same hit id appears in multiple provider search rows with changed URL, creation time, kind, claim state, operation id, owner, semantic signature, or `evidence_sha256`, the packet emits `CONFLICTING_HIT_METADATA:<id>` and status becomes `UNKNOWN_HOLD`. Identical repeated evidence is allowed and its evidence origins are aggregated.

This closes a dangerous false-CLEAR class where contradictory versions of the same provider hit could previously be skipped as semantically unrelated before contradiction detection.

## Time contract

`search.observed_at` cannot be future-dated **or predate `candidate.created_at`**. Every required provider/family/term observation must occur at or after the candidate intent epoch, closing the gap where an earlier competing TAKE could appear after a stale census but before candidate creation. A hit created after `evaluation_time`, or after the exact search row that allegedly observed it, yields `UNKNOWN_HOLD`; it is never treated as a harmless later duplicate. A legitimate later duplicate may still be reported when it postdates the candidate but predates its provider observation and evaluation.

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

`CLEAR_ON_SUPPLIED_EVIDENCE` means only that the supplied census satisfied this deterministic contract. A seat still follows live provider-search, current-owner, Muse/outbound, repository, and merge policies. This tool performs no provider/network mutation and makes no customer, revenue, payment, savings, or legal conclusion.
