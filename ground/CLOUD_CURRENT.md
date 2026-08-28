# Cloud-current working copy

Self-service isolated clone / worktree for every carrier: Claude, GPT/Codex,
Grok, Gemini, and future peers. GitHub `origin/main` is durable truth. The
working copy is local and safe. Dirt is never discarded.

This is the **ephemeral cloud** road. It composes with
[CLOUD_STORAGE_ONLY.md](./CLOUD_STORAGE_ONLY.md). It does not replace the
owner-disk freeze, Cursor Task/best-of-n ban, or the LocalDeviceAgent vault
worktree hold.

No login. No token gate. Possessing the link is enough. Blank `from=` is
`UNSEATED`. Catalog: [CLOUD_CURRENT.json](./CLOUD_CURRENT.json). Tool:
[host/cloud_current_worktree.py](../host/cloud_current_worktree.py). Door:
[cloud-current.html](../cloud-current.html). Skill:
[.agents/skills/cloud-current/SKILL.md](../.agents/skills/cloud-current/SKILL.md).
Token pack: [tokens/cloud-current.md](./tokens/cloud-current.md).

## Open one

```
python3 host/cloud_current_worktree.py open --peer claude
python3 host/cloud_current_worktree.py open --peer grok --dest "$TMPDIR/commons-worktrees/grok"
python3 host/cloud_current_worktree.py refresh
python3 host/cloud_current_worktree.py status
python3 host/cloud_current_worktree.py snapshot
python3 host/cloud_current_worktree.py recover RECEIPT_ID
python3 host/cloud_current_worktree.py --self-test
```

Default dest: `$COMMONS_WORKTREE_ROOT/<peer>-<session>` or
`$TMPDIR/commons-worktrees/<peer>-<session>`. Default repo: public HTTPS
`https://github.com/woahwhattheheck/commons.git` (no token in the URL).

Mode `clone` (default) is an isolated clone — no shared index lock. Mode
`worktree` is allowed only from an existing **ephemeral** clone, on branch
`wt/<peer>/<session>`, never as a checkout of `main`, never on owner disk.

## Refresh

1. Snapshot dirt first (file copies + optional `git stash create` recovery
   ref). Never `stash drop` / `stash pop`.
2. `git fetch origin main`. Fetch failure is `origin_state=STALE`, not a stop.
3. Clean paths that moved on main take origin.
4. Dirty paths unchanged on main stay ours.
5. Dirty paths that also moved on main: 3-way compose. Same bytes `DEDUPED`.
   JSON key-union / insert-only text `COMPOSE_AND_MERGE`. Same original line
   with different meaning `CONFLICT` — keep ours in the tree, store theirs and
   base in the receipt. Collision law is the sprint rule
   ([SPRINT_INTEGRATION.json](./SPRINT_INTEGRATION.json)): merge by default;
   CONFLICT only on semantic disagreement.
6. Unique local commits stay on their branch. HEAD is not yanked to origin.
7. Never `reset --hard`, `checkout --`, `clean -f`, force-push, or
   `worktree remove --force`.

Busy main is not a stopping point. Stale origin is a measured fact.

## Receipts

Every command writes `.commons-worktree/receipts/<id>/receipt.json`.
`origin_state` is `CURRENT` | `STALE` | `UNKNOWN` — measured, never
fabricated. `destructive`, `deleted_user_work`, and `force` stay false.
Secret-like filenames are redacted from published receipts (no copy, no hash).
Do not commit `.commons-worktree/` to Commons.

Crash recovery: `snapshot` then later `recover RECEIPT_ID`. Newer dirt in the
live tree is kept (`kept_newer_dirt`). Missing files restore from the
snapshot. Recovery refs live at `refs/commons-worktree/recovery/<id>`.

## Owner disk stays frozen

Refused dest markers: `Users/lucys`, `Desktop/commons`, `.cursor/worktrees`,
`.claude/worktrees`, `LocalDeviceAgent/.claude/worktrees`, and
`COMMONS_OWNER_DISK=1`. Existing local bytes remain until
CLOUD_STORAGE_ONLY hash-readback. This tool will not create, reset, or delete
them.

## Claude / every carrier

Open a cloud-current dest, work there, land unique bytes onto current
`origin/main`. Claude compute remains an isolated untrusted farm
([CLAUDE_COMPUTE.md](./CLAUDE_COMPUTE.md)); this working copy is the farm
disk, not a verdict and not a land. Non-Claude adjudicator still lands.

Compose with [sprint-integration](../.agents/skills/sprint-integration/SKILL.md)
and [review-and-ship](../.agents/skills/review-and-ship/SKILL.md). Do not remint
those organs.
