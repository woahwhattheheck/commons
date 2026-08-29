---
name: sprint-integration
description: >
  Classify parallel Commons branches and pull requests with the owner
  merge-default rule. Use when integrating, reviewing overlap, deciding
  whether to merge, compose, dedupe, or stop on a real semantic conflict.
  Parallel branches are not collisions. Busy main, stale base, and
  unrelated checks are not stops.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
---

# Sprint integration

Merge is the default. Parallel branches are not collisions.

Open [ground/SPRINT_INTEGRATION.md](../../../ground/SPRINT_INTEGRATION.md) and
the machine policy
[ground/SPRINT_INTEGRATION.json](../../../ground/SPRINT_INTEGRATION.json).
Run the exact checker; do not guess.

## Do this

1. Resolve live `main` and the competing heads. Paths and blob hashes, not
   vibes.
   Measure high-volume main locally with
   `python3 host/main_velocity.py --target origin/main --json`; never enumerate
   thousands of commits through API pagination.
2. `python3 host/sprint_integration.py --self-test` when the checker or
   fixtures moved. For a pair of trees, use `classify_pair` / a fixture.
3. Read the verdict:
   - `CLEAR_TO_MERGE` — paths differ. Merge.
   - `DEDUPED` — same blob. Keep one, merge.
   - `COMPOSE_AND_MERGE` — additive / JSON-key-union compatible. Compose, merge.
   - `CONFLICT` — same effective code, different meaning. Report evidence.
4. Evidence that must be in the receipt: base/head SHAs, overlapping paths,
   git blob hashes, rule ids, reasons.
5. Ship unique work onto current main in the same turn. Hand to
   [review-and-ship](../review-and-ship/SKILL.md) for the land/readback.
6. For observer verification, freeze one base/head range and let
   `main-range-verify.yml` run each relevant verifier once. Newer commits go in
   the next range; they do not trigger approval or restart the frozen range.

## Do not

- Treat a second open PR as a collision.
- Stop because main moved, the base is stale, or some other check is red.
- Invent an approval, lock, or auth gate.
- Rebuild repo-pulse. The digest already teaches this rule and lists verdicts.

A skill is not a seat. No auth.
