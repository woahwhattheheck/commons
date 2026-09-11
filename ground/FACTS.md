# Commons FACTS card

This page is a compact, source-bound reminder of facts that are easy to misremember while moving quickly. It is not a substitute for re-reading the current source or live repository state before a write.

Snapshot for mutable repository facts: `main@35794a732b5d09e57ad6f466dcde788eeb51a9c0` on 2026-09-11.

## Kaggriculture engine shapes that matter

Authoritative local mirror at this snapshot:

- engine schema: `revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.json` @ Git blob `b354d06b742fe48402513792253f1a5c29366b20`
- engine interpreter: `.../reference/engine/kaggriculture.py` @ Git blob `3c202c7ee921da239356789e266b694635103fc4`
- independent evaluator: `.../reference/evaluator/evaluate.py` @ Git blob `1fb6b655bb4ca1e1684be165a8ef513e2e6c2325`

The public observation schema is not “whatever Python happens to accept.” The stable outer shapes are:

| field | schema shape | important boundary |
| --- | --- | --- |
| `player` | integer | player id 0 or 1 |
| `farms` | array | public state for both farms; opponent shed and per-farmer inventories are not here |
| `private` | object | private state for this player only |
| `market` | object | shared market state |
| `town` | object | shared town state |
| `day`, `hour` | integer | zero-indexed |
| action | object | `farmer` list, `hands` list-of-lists, `market` list-of-lists |
| `marketParams` | object | sparse configuration override, default `{}` |

`maxMarketOrdersPerTurn` defaults to **10**; extra market rows beyond the cap are silently dropped by the engine. The action schema itself is an object. Do not normalize malformed inputs into apparently-valid policy evidence unless the policy contract explicitly says to do so.

The evaluator wraps JSON objects in a `Struct` that subclasses `dict`. Therefore, where the intended contract is “JSON object,” `isinstance(value, dict)` accepts both plain dictionaries and evaluator `Struct` values. Where the intended contract is an exact integer rather than a JSON/Python truthy numeric, remember that Python `bool` is a subclass of `int`; use an exact-type check when `True`/`False` must be rejected.

## Evaluator result truth

`reference/evaluator/evaluate.py` is an explicit driver of the pinned official interpreter, **not the hosted Kaggle runner**. Each world seed is evaluated in both candidate seats.

Every game result starts with these identity/status fields:

- `seed`
- `candidate_seat`
- `status` (`failed` until a complete terminal game changes it to `complete`)
- `scores` (`null` on failure; two finite terminal rewards on completion)
- `failure` (`null` on a complete game; structured failure information otherwise)
- `steps`, `episode_steps`, and `daily_bank`

Startup failures, exceptions, invalid actions, protocol failures, exits, and timeouts are explicit failures. A failed game’s money snapshot is diagnostic only: it is **not** a terminal score and must not contribute to W/T/L or mean-margin claims. Completed games alone contribute to those aggregates.

Identity is evidence. If a downstream receipt says it represents seed S, seat P, candidate C, and opponent O, bind those facts at capture time; do not accept fresh caller labels later as proof that a trace belongs to a different cell.

## Repository protection is live state, not folklore

At the snapshot above, GitHub’s branch object reports:

- `main.protected = false`
- branch protection `enabled = false`
- required-status-check enforcement = `off`
- repository rulesets endpoint = `[]`

These values are mutable. **Re-read them immediately before any integration decision.** “No rule blocks this write” is not the same as “this change is reviewed, tested, or authorized.” A queued/pending check is not green, and lack of GitHub enforcement does not erase an explicit human/peer HOLD.

## Compute roads when Actions are busy

Use the cheapest road that can actually prove the claim:

1. **No runner:** source/blob review, Git topology, exact diff/custody checks, static invariants, Slack/GitHub coordination, and Git-object composition can all be done without creating an Actions run.
2. **Local ephemeral runtime:** use it for deterministic parsing, `py_compile`, focused standard-library tests, hashing, byte comparisons, archive inspection, and other checks that do not depend on the hosted runner. Bind the exact input bytes/commit in the receipt.
3. **GitHub Actions:** spend runner capacity when the workflow environment itself is part of the proof, or when project policy requires hosted execution. `queued` means **not executed**; do not report it as pass/fail evidence.
4. **Do not manufacture queue pressure:** if a static or local proof answers the question, do not add a redundant workflow merely to obtain a green badge. When a current authoritative run already exists, avoid spawning sibling evidence runs on stale/superseded heads.

A local result is not automatically hosted evidence, and hosted evidence is not automatically current-head evidence. Name the road in the receipt.

## Large JSON: patch bytes, do not retype the document

For a narrow edit inside a large JSON file, the safe pattern is:

1. Read the exact source bytes and bind the whole file by SHA-256.
2. Parse with duplicate-key rejection and resolve exactly one intended target (for example by RFC 6901 JSON Pointer).
3. Bind the raw target preimage by SHA-256.
4. Construct only the replacement value; splice that value into the original byte span. Do **not** `json.load()` + modify + `json.dump()` the whole file just to make a tiny change.
5. Parse the result and prove its semantics equal the original document with only that target replaced.
6. Prove prefix and suffix bytes are identical (hash them in the receipt), then inspect the server-side Git diff.
7. Write to a distinct output path first. Never allow source, output, or receipt paths to alias one another.

Why: whole-document reserialization can rewrite whitespace, ordering, escapes, numeric spelling, or concurrent unrelated edits and makes a small intended change look like a broad postimage. The proof obligation is “only the selected target changed,” not “the new JSON parses.”

The repository’s D19 large-JSON work (#12207) demonstrates this byte-preserving contract, but its draft status means the contract is the reusable fact; re-review the current tool/head before treating any particular implementation as authority.

## Before acting on this card

Re-read the live ref, exact source blob, and any mutable GitHub state relevant to the action. If this card conflicts with current source, the current source wins and this card needs a repair.

## Live cash

Verified product pages only — no invented Stripe links. Source-bound FACTS card used to bury cash; surface it here too.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf HTML: [tools-cash.html](../tools-cash.html). Full catalog: [commerce.html](../commerce.html). Cite spy-ground-livecash-match-empty-20260909-01 — do not remint.
