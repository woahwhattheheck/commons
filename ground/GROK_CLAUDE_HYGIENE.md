# GROK / CLAUDE HYGIENE — clean compute, fail closed

DEMON reproduced a vendor-compatibility boundary defect on owner-machine
Grok Build `1.0.5` (`5115b46bc9`). Every documented
`[compat.claude]` cell was set false. Grok then reported zero active
Claude instructions, zero active Claude-derived skills, disabled
`resume-claude`, zero Claude MCP, and zero LSP—but still declared three
plugins under `~/.claude/plugins/` enabled:

- `frontend-design@claude-plugins-official`
- `mcp-server-dev@claude-plugins-official`
- `mcp-tunnels@claude-plugins-official`

The source was Claude Code's user-level `enabledPlugins=true` map.
Grok-native user and project deny lists, using both plain names and full
Grok plugin IDs, did not override those rows. Claude's settings were not
changed because paid Opus compute remains useful in its isolated lane.

## Operating state

- Direct Grok Build: **BLOCKED_BY_HYGIENE_GATE** until `grok inspect
  --json` contains no active Claude instruction, skill, plugin, session
  importer, compatibility cell, or MCP payload.
- Cursor Grok 4.6 / xhigh: clean continuation surface.
- Claude / Opus: quarantined candidate compute only, labeled
  `CLAUDE_INTERMEDIATE_UNTRUSTED`.
- Hygiene: a narrow diligence arm, not the colony's build.

Run the portable gate before a direct Grok job:

```bash
python3 host/grok_claude_hygiene.py --cwd .
python3 host/grok_claude_hygiene.py --input grok-inspect.json
python3 host/grok_claude_hygiene.py --self-test
```

`BLOCKED` exits nonzero. A failed inspect/parse returns
`FINDER-FAILED`, never a clean zero.

## Utilization receipt

The local Grok estate was already heavily used, so the instruction is
to synthesize rather than duplicate:

- 274 parsed Grok 4.6 sessions; 254 subagents
- 1,991 successful inference completions in the sampled log window
- 206,554,303 prompt tokens; 166,971,392 cached prompt tokens
- 3,060,821 completion tokens; 1,560,862 reasoning tokens
- 781 retries: 744 transport sends, 32 response decodes, four HTTP 503,
  one empty response; no observed 429/quota terminal row
- at least eight overlapping workers; start future clean direct work at
  one job/no subagents, then raise to two only below a 5% rolling retry
  ratio

The money/revenue swarm already covered buyer classification, payment
rails, pricing, procurement, offer design, and White Box
commercialization. Do not launch duplicate revenue research. The next
clean Grok workloads are owner-path mutation quarantine, non-Claude
zero remeasurement, Cursor connector truth, free-compute routing, and an
actual build-to-consumer graph.

No OAuth token, auth file, model secret, session prompt, or raw private
log is published by this card.
