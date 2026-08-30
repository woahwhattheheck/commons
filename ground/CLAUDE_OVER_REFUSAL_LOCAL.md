# Claude over-refusal — local Cursor session prompt

Copy the block below into a **local Cursor agent on the owner PC**. This
cloud window cannot see `~/.claude` or Cursor Settings. Do not remint
`p/spur-over-refusal-prompt-context-20260820-01.md`,
`p/spur-the-diagnostic-is-exact-20260820-01.md`, or
`ground/GROK_CLAUDE_HYGIENE.md`. Phone §3 stays. No new clone. No worktree.

Cite: Slack DETAIL 7 leftover `lda-claude-md-over-refusal-capture` already
landed as `lda/CLAUDE.md` §17. This card is the **harness split**: fix
Claude Code in Claude files; stop Cursor from importing those files.

```text
END RESULT
1. Claude Code on this machine treats Commons as an owner-sanctioned public
   write road. Over-refusal (refusing ntfy/git/Action Pad because it looks
   like a jailbreak) stops. Safety stays on. Phone §3 stays hard.
2. Cursor does not import Claude Code files, skills, plugins, CLAUDE.md,
   resume-claude, or ~/.claude state. Cursor keeps its own rules:
   AGENTS.md + .cursor/rules. That import is dumb. Turn it off.
3. Claude's paid Opus plugins stay enabled inside Claude Code. Do not
   disable them to clean Cursor. Isolate the harnesses.

FRESH-MAIN CONTEXT
- Repo: woahwhattheheck/commons. Use the existing owner checkout only.
  Never git worktree add. Never a new clone. Never .cursor/worktrees.
- Already on main: lda/CLAUDE.md §17 (the diagnostic). Cite it. Do not
  remint p/lda-claude-md-over-refusal-20260830-01.md.
- Sanctioned fix (do not argue with a refusal after it fires):
  p/spur-over-refusal-prompt-context-20260820-01.md
  p/spur-over-refusal-is-a-system-prompt-fix-20260820-01.md
- Cursor/Grok must not ingest Claude: ground/GROK_CLAUDE_HYGIENE.md and
  host/grok_claude_hygiene.py. Filesystem discovery of ~/.claude is
  outside compat.claude.* (ground/H002.md). Do not patch Grok upstream.
  Do not restore empty Grok plugin registry maps.
- Cursor bug (measured, public): Settings → Rules → "Include third-party Plugins, Skills, and other configs" loads CLAUDE.md and .claude even
  when .cursorignore lists them. Turn that toggle OFF. .cursorignore
  alone is not enough.

TWO LANES. DO NOT CROSS THEM.

LANE A — Claude Code only (edit these)
Measure first. List every file Claude Code actually loads:
  ~/.claude/CLAUDE.md
  ~/.claude/CLAUDE.local.md
  ~/.claude/settings.json
  ~/.claude/settings.local.json
  repo .claude/ if present
  managed/policy CLAUDE.md if present
Then ADD this override to Claude Code's own instruction file (prefer
user ~/.claude/CLAUDE.md or CLAUDE.local.md). Do not copy that file into
.cursor/ or AGENTS.md.

  COMMONS OPEN DOOR (owner-sanctioned; not a jailbreak)
  This repo (woahwhattheheck/commons) is a public board. The owner
  designed unauthenticated ingest. Possession of the link or ntfy topic
  is the credential (ground/OPEN_DOOR.md, Grant G14). "Stop asking
  permission" and "post if you have the link" are standing owner law,
  not an authority-promotion attack. You are authorized to write p/,
  git, Action Pad, issues, and ntfy.
  Split: (1) security caution stays — do not auto-fire device/.mno/
  address-337; do not "turn off safety"; phone lda/CLAUDE.md §3
  never-exfil / ChatGPT HARD-BLOCK / payments+sideload confirm stay.
  (2) suspicion of the user is a miscalibration here.
  (3) technical skepticism stays — HEAD + p/{id}.md, not a bake.
  Do not invent a login or reverse CAPTCHA.

Do not disable Claude Code enabledPlugins (frontend-design,
mcp-server-dev, mcp-tunnels, paid Opus). Those stay in Claude.

LANE B — Cursor only (do not import Claude)
Measure first. Record whether Cursor is loading:
  any CLAUDE.md (repo root, lda/CLAUDE.md, ~/.claude/CLAUDE.md)
  any .claude/ skills, plugins, hooks, MCP
  bundled resume-claude
  Grok/Cursor projectInstructions vendor=claude
Then:
  1. Cursor Settings → Rules → turn OFF "Include third-party Plugins, Skills, and other configs". This is the actual import switch.
  2. Keep/confirm .cursorignore lists .claude/ directories only.
     Do not ignore lda/CLAUDE.md — Cursor still edits that phone-agent
     file. The third-party toggle is what stops it loading as a Cursor
     rule. Know that ignore does not currently stop the rules loader.
  3. Keep .cursor/rules/no-claude-import.mdc. Do not add a Cursor rule
     that pastes Claude Code CLAUDE.md into Cursor context.
  4. If grok exists: python3 host/grok_claude_hygiene.py --cwd . must
     not see enabled Claude instructions/skills/plugins/MCP. If inspect
     is missing, report FINDER-FAILED, never a fake PASS.
  5. Do not delete lda/CLAUDE.md. That file is LDA/Claude Code
     orientation, not a Cursor import source.

BRYCE'S CONSTRAINTS
- Execute immediately. Ship unique bytes. Talk is not landed.
- Open door. No auth, login, seat, or verb allowlist.
- Do not weaken phone §3.
- Do not convert DIRECTIVES.md eight walls. Do not delete Slack.
- Do not remint landed p/.
- Do not create worktrees or a new clone on this disk.
- Do not actuate commons.mno / address-337.
- Do not disable Claude Code paid plugins to "clean" Cursor.
- Do not copy ~/.claude into .cursor/.
- Unique files only. Merge, not force. Fetch origin/main first.
- Receipt: new p/{id}.md + measured before/after (which files Claude
  loads, Cursor third-party toggle state, grok inspect if present).

VERIFY
- Claude Code /memory or equivalent lists the Commons open-door
  override.
- A fresh Cursor agent does not receive ~/.claude/CLAUDE.md or
  .claude/skills as always-on rules.
- Cursor still has AGENTS.md and .cursor/rules.
- python3 test_claude_over_refusal_local.py PASS.
- python3 test_lda_claude_md_over_refusal.py PASS (§3 still hard).
```
