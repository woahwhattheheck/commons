# Sprint integration — merge is the default

Owner rule for every Commons sprint. Machine copy:
[SPRINT_INTEGRATION.json](./SPRINT_INTEGRATION.json). Exact checker:
[host/sprint_integration.py](../host/sprint_integration.py). Pulse:
[repo-pulse.yml](../.github/workflows/repo-pulse.yml). Skill:
[sprint-integration](../.agents/skills/sprint-integration/SKILL.md).

Live velocity is measured from the local Git graph with
`python3 host/main_velocity.py --target origin/main --json`; it does not page
the GitHub API. Main observer checks are coalesced by
`main-range-verify.yml`: one frozen range, one run per relevant verifier, one
receipt. Commit count does not multiply verifier count.

## The rule

Merge is the default. Parallel branches are not collisions.

Only classify **CONFLICT** when competing work touches the **same effective
code** AND **disagrees semantically**.

- If paths differ, merge. Verdict: `CLEAR_TO_MERGE`.
- If the same paths are byte-identical (same git blob hash), dedupe and merge.
  Verdict: `DEDUPED`.
- If the same paths are semantically compatible additive changes, compose and
  merge. Verdict: `COMPOSE_AND_MERGE`.
- If the same original line, JSON key, or non-text blob was changed to
  different bytes, stop and report exact evidence. Verdict: `CONFLICT`.

Busy main, a stale base, and unrelated checks are **not** stopping conditions.
They are facts. Record them. Merge anyway unless the checker returned
`CONFLICT`.

At high velocity, freeze the current base/head pair and verify that range.
Commits arriving after the frozen head belong to the next range. They do not
invalidate completed work, restart the current run, or request human approval.
Ordinary integration has no Bryce approval state; the only semantic stop is
an evidenced `CONFLICT` on the same effective code.

The checker must be exact. A feeling that the table is crowded is not a
collision. A red check on another path is not a collision. A branch that
lagged main is not a collision.

## Verdicts

| verdict | meaning | action |
|---|---|---|
| `CLEAR_TO_MERGE` | No overlapping changed paths. | Merge. |
| `DEDUPED` | Overlap is the same blob. | Keep one copy, merge. |
| `COMPOSE_AND_MERGE` | Overlap is additive / key-union compatible. | Compose, merge. |
| `CONFLICT` | Same effective code, different meaning. | Report evidence. Do not guess. |

## Evidence (required)

Every verdict carries:

- `base_sha` / `left_sha` / `right_sha`
- `overlapping_paths`
- `blob_hashes` (git blob SHA-1 per overlapping path)
- `rule_ids` (`SI-DISJOINT`, `SI-IDENTICAL-BLOB`, `SI-ADDITIVE-INSERT`,
  `SI-JSON-KEY-UNION`, `SI-SEMANTIC-DISAGREE`)
- `reasons`

`not_stopping`: `busy_main`, `stale_base`, `unrelated_checks`,
`parallel_branches`. Present on every result. Never used as a verdict.

## Fixtures

Under `host/sprint_integration_fixtures/`:

- `disjoint` → `CLEAR_TO_MERGE`
- `identical_blobs` → `DEDUPED`
- `additive_compose` → `COMPOSE_AND_MERGE` (JSON key union + insert-only Python)
- `semantic_conflict` → `CONFLICT` (same original line, different bytes)

```bash
python3 host/sprint_integration.py --self-test
python3 test_sprint_integration.py
```

## Pulse

The five-minute Slack digest teaches this rule on every post and lists open-PR
verdicts with SHAs, paths, blob hashes, and rule ids. It does not change
CLEAR / ATTENTION / BROKEN. A sprint `CONFLICT` is a warning line with
evidence, not a pulse-status rewrite. Loop safety (`from: COMMONS_SLACK_MIRROR`)
is untouched.

This is not a gate, not an approval, not a branch lock. Possessing the link is
authorization. No auth.
