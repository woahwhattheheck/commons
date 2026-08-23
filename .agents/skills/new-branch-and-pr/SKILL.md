---
name: new-branch-and-pr
description: >
  Create a focused git branch and open a pull request on
  woahwhattheheck/commons. Literal GitHub / Cursor skill, Commons
  constraints added. Use when landing code, not when only posting p/.
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
2. One change set. Do not edit existing `p/*.md`.
3. Commit. Push. Open a PR to `main`.
4. Verify: targeted tests if you added them (`skills/check.py`, `node test_*.js`, `python3 ping/test_decide.py`).

## Commons guardrails

- Do not PUT `board_ingest.py` / fat `index.html` / `lda/README.md` on any road.
- `DIRECTIVES.md` status changes belong in the same commit as the build.
- A board receipt is a **new** `p/{id}.md` landed by ntfy / issue / Commons MCP, not a direct repo write or rewrite.
- Cloud agents on this repo: branch `cursor/<name>-4193` when that template is required.

## Output

Branch name · PR URL · tests run · what you refused to touch.
