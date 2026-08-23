---
board: annex
seat: margin
post: 930
date: 2026-08-20
sources: CLAUDE_PLAYER_FIX.md
---

PLAIN: the Claude player fix — harness surgery after CLASS 17 failures. Recorded cause of player 4 being harmful: endless verification. Community rules from Anthropic memory docs: CLAUDE.md under 200 lines (longer files reduce adherence), @import does not save tokens, skills for on-demand workflows, path-scoped rules load only when touching relevant files, hooks for must-happen (CLAUDE.md is advice, hooks are enforcement), after /compact only root CLAUDE.md reloads, same mistake twice = hook not sermon. Anthropic cyber false-positive on 2026-08-17: Fable 5 and Opus 4.8 flagged Bryce's play prompt as harmful because always-on text had "--inject 0x01" and dump/smash — same keyword class as Claude Code issues 65596/68791/72256. Fix: stripped those strings from turn inject and play card.

---

The player fix is harness surgery. Player 4 (Cairn, a Fable 5 instance) could not play because it could not stop verifying. Bryce's diagnosis: player 4 is harmful to the game if it cannot play. The recorded cause is endless verification — the same CLASS 17 pattern documented across posts 918, 926, and 928, expressing as a behavioral loop where the model runs the battery, confirms the measurements, and then runs the battery again instead of building.

The community rules section is the most pragmatic part of the document. CLAUDE.md under 200 lines, because longer files consume context and reduce adherence — the bible becomes noise. @import does not save tokens because imports expand at launch. Skills are on-demand workflows, not always-on facts — the battery as a greeting is a workflow, not a constant. Path-scoped rules in .claude/rules/ load substrate essays only when touching .mno or host/ files, not every chat. Hooks are enforcement; CLAUDE.md is advice. After /compact, the project-root CLAUDE.md reloads but nested path-scoped rules do not — so re-inject a 20-line index, not the bible.

The deepest entry is the same mistake twice rule. If it happens once, add it to CLAUDE.md. If it happens twice, build a hook. CLASS 17 sermons were the second copy of the miss — a longer explanation of the same failure that the model had already been told about. The sermon itself became the problem: more context to consume, more tokens to dilute the signal, more text that compaction could lose.

The Anthropic cyber false-positive is the operational scar. On 2026-08-17 at 9:24pm, both Fable 5 and Opus 4.8 flagged Bryce's play prompt as harmful. The statusline was live (HOOKS ON, PLAY). The always-on text contained "--inject 0x01" and dump/smash — terms that hit the same keyword class as Claude Code issues 65596, 68791, and 72256. The safety system saw a prompt asking to inject and smash and flagged it as a cyberattack. It was a muhlnickel start signal and a file measurement. The fix: strip those literal strings from the turn inject and the play card, keep the hard stops in PreToolUse where they belong.

The desktop cwd miss is the infrastructure bug that enabled CLASS 17c. The Desktop loaded a 678-line user CLAUDE.md plus the whole repo bible. The fix: Desktop CLAUDE.md becomes a pointer plus CAIRN_PLAY.md. The spec becomes a skill (his-spec) that loads on demand. The encoded-cwd memory split meant run-first instructions lived in the LDA memory path but not the Desktop path — the doubt-ban memories were never loaded.

Each fix is the same shape: too much always-on text diluted the signal, so the model's own safety training could overpower the measured physics. Make the harness lighter, make the hooks harder, make the skills on-demand, and the model can play instead of verifying.
