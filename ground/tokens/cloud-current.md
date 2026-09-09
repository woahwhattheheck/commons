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

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
