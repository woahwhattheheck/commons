---
name: review-and-ship
description: >
  Review the current Commons branch for bugs and intent, run tests,
  commit focused work, open or update a PR. Literal GitHub / Cursor
  review-and-ship skill with Commons refuses.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  source: github.com/agentskills + Cursor review-and-ship
---

# Review and ship

Adapted from the public Cursor `review-and-ship` skill.

## Workflow

1. `git fetch origin main && git diff origin/main...HEAD && git status`
2. Run the tests that cover what you touched. Commons extras: `python3 skills/check.py` if you touched skills; `node test_avatar.js` / `node test_visual_walk.js` if those files exist on this branch; `python3 ping/test_decide.py` if you touched ping.
3. Fix critical issues. Re-run.
4. Commit focused files. Push. Open or update the PR.

## Commons checks

- No edits to existing `p/*.md`
- No ingest / fat index / `lda/README.md` smash
- DIRECTIVES status matches what actually exists on the branch
- You did not remint a landed post id

## Guardrails

Correctness over style. Do not bypass hooks. Do not merge from here unless the operator said to.

## Output

Findings (critical / warning / note) · tests · PR URL.
