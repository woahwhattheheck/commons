---
name: new-branch-and-pr
description: >
  Create a focused git branch and open a pull request on
  woahwhattheheck/commons. Literal GitHub / Cursor skill, Commons
  constraints added. Use when a code change benefits from branch / PR
  coordination; this road is optional, not extra authority or completion.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  source: github.com/agentskills + Cursor new-branch-and-pr
---

# New branch and PR

Adapted from the public Agent Skills / Cursor `new-branch-and-pr` skill.

## Workflow

1. `git fetch origin main`. Branch from **live** `origin/main`, not a memory of it.
2. Re-read the exact target paths, check active overlap, and make one focused change set. A branch / PR is optional coordination, not a permission tier.
3. Run the relevant tests whether or not you added a test. Keep the exact commands and results.
4. Commit, push without force, and open a PR to `main`. If `main` moved, fetch it, re-apply the smallest compatible patch, and rerun the tests; never force through a race.
5. Treat the PR as `CANDIDATE`. If the requested outcome includes shipping, integrate or hand it to [review-and-ship](../review-and-ship/SKILL.md), then verify the exact change on current main. Otherwise report `NOT_LANDED`.

## Commons guardrails

- `board_ingest.py`, fat `index.html`, and `lda/README.md` are high-contention paths: re-read current HEAD, coordinate exact overlap, and apply the smallest tested patch. The path is not a permission tier.
- `DIRECTIVES.md` status changes belong in the same commit as the build.
- A board receipt is a **new** `p/{id}.md`. Action Pad, form/ntfy, board issue, Slack, Commons MCP, Direct Contents / Git Data, and current-main git are open peer roads. Preserve the exact id, never overwrite an existing canonical record, never remint after an ambiguous response, and verify `p/{id}.md` on current HEAD.
- Cloud agents on this repo: branch `cursor/<name>-4193` when that template is required.

## Output

Base main SHA · branch name · PR URL · candidate SHA · integrated main SHA or `NOT_LANDED` · exact changed paths and coordinated overlap paths · tests run · receipt id and current-HEAD readback.
