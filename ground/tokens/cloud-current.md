# Tokens — cloud-current working copy

GitHub `origin/main` is durable truth. Local is a safe working copy.

```
python3 host/cloud_current_worktree.py open --peer YOUR_CLAIM
python3 host/cloud_current_worktree.py refresh
python3 host/cloud_current_worktree.py status
```

Facts:

- Isolated dest. Default `$TMPDIR/commons-worktrees/<peer>-<session>`. Never owner disk.
- Refresh snapshots dirt first. Fetch failure is `STALE`, not a stop.
- Compatible parallel changes merge. CONFLICT only when the same effective code disagrees semantically; then keep ours and record theirs.
- Never `reset --hard`, force-push, `checkout --`, `stash drop`, or `clean -f`.
- Receipts are measured (`CURRENT` / `STALE` / `UNKNOWN`). Do not fabricate readiness.
- Do not commit `.commons-worktree/` or secret-like files.

Owner-disk freeze unchanged: [CLOUD_STORAGE_ONLY.md](../CLOUD_STORAGE_ONLY.md).
Law: [CLOUD_CURRENT.md](../CLOUD_CURRENT.md). Door: [cloud-current.html](../../cloud-current.html).
Skill: [cloud-current](../../.agents/skills/cloud-current/SKILL.md).
Land unique bytes on current main: [LAND.md](../LAND.md).
