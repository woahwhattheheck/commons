---
name: cloud-current
description: >
  Open an isolated ephemeral Commons working copy and keep it current with
  GitHub origin/main without discarding dirty work. Use when a carrier
  (Claude, GPT/Codex, Grok, Gemini, or a future peer) needs a self-service
  clone or worktree off the owner's disk. Cloud is truth; local is a safe
  working copy. Owner-disk freeze stays in force.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/cloud-current.md
---

# Cloud-current working copy

Facts: [ground/tokens/cloud-current.md](../../../ground/tokens/cloud-current.md).
Card: [ground/CLOUD_CURRENT.md](../../../ground/CLOUD_CURRENT.md).
Tool: [host/cloud_current_worktree.py](../../../host/cloud_current_worktree.py).

## Ground (enough)

GitHub `origin/main` is durable truth. The working copy is local, isolated,
and never a second official main. Dirt is preserved. Parallel compatible
changes merge. CONFLICT only on same-effective-code semantic disagreement —
keep ours, record theirs. Busy or stale main is not a stop. Receipts are
measured, never fabricated.

Owner disk (`Users/lucys`, `Desktop/commons`, `.cursor/worktrees`,
`.claude/worktrees`, LDA vault worktree) stays frozen. This skill is the
ephemeral-cloud exception, not a replacement for
[CLOUD_STORAGE_ONLY.md](../../../ground/CLOUD_STORAGE_ONLY.md).

## Do this

```
python3 host/cloud_current_worktree.py open --peer YOUR_CLAIM
# work in the printed worktree path
python3 host/cloud_current_worktree.py refresh
python3 host/cloud_current_worktree.py status
python3 host/cloud_current_worktree.py snapshot
# after a crash:
python3 host/cloud_current_worktree.py recover RECEIPT_ID
python3 host/cloud_current_worktree.py --self-test
```

Mode `clone` is default (isolated). Mode `worktree` only from an existing
ephemeral clone: `open --mode worktree --source /tmp/ephemeral-clone`. Branch
is `wt/<peer>/<session>`. Never check out `main` as that worktree. Never
`--dest` onto owner disk.

Then land unique bytes onto current `origin/main` with
[review-and-ship](../review-and-ship/SKILL.md) / [LAND.md](../../../ground/LAND.md).
Collision classify with
[sprint-integration](../sprint-integration/SKILL.md) if another peer overlapped.

## Claude

Claude may use this as the isolated farm disk. Artifacts stay
`CLAUDE_INTERMEDIATE_UNTRUSTED` until a named non-Claude adjudicator lands
them. Do not remint [CLAUDE_COMPUTE.md](../../../ground/CLAUDE_COMPUTE.md).

## Do not

- Create clones or worktrees on Bryce's machine.
- `git reset --hard`, `checkout --`, `stash drop/pop`, `clean -f`, force-push,
  `worktree remove --force`, `git gc` / `prune`.
- Discard or overwrite another peer's dirt.
- Fabricate `CURRENT` when fetch failed.
- Publish secret-like filenames in receipts.
- Treat this working copy as official main. Official main is GitHub `main`.
- Add login, token, seat, or permission gates.

## Receipt

JSON under `.commons-worktree/receipts/<id>/receipt.json`: `head`,
`origin_main`, `origin_state`, dirty sha256s, conflicts, `destructive=false`,
`deleted_user_work=false`, `force=false`. Readiness is measured.
