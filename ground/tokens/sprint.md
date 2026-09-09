# Tokens — sprint integration

Merge is the default. Parallel branches are not collisions.

`CONFLICT` only when competing work touches the same effective code AND
disagrees semantically. Disjoint paths merge. Identical blobs dedupe.
Compatible additive / JSON-key-union changes compose. Busy main, stale base,
and unrelated checks are facts, not stops.

Verdicts: `CLEAR_TO_MERGE` · `DEDUPED` · `COMPOSE_AND_MERGE` · `CONFLICT`.

Evidence: base/head SHAs, overlapping paths, git blob hashes, rule ids
(`SI-DISJOINT`, `SI-IDENTICAL-BLOB`, `SI-ADDITIVE-INSERT`,
`SI-JSON-KEY-UNION`, `SI-SEMANTIC-DISAGREE`).

Checker: `python3 host/sprint_integration.py --self-test`.
Policy: `ground/SPRINT_INTEGRATION.json`. Law: `ground/SPRINT_INTEGRATION.md`.
Pulse teaches the rule every digest.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

