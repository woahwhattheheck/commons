# CURSOR QUOTA HOLD — SuperGrok Heavy / Grok Build is the Grok lane

Owner correction, 2026-08-25: the colony was told to use the paid SuperGrok
Heavy / Grok Build subscription pool and not Cursor. Cursor usage consumed a
reported 30% of a separately reserved quota. That routing error is retracted.

This card extends the already-landed `ground/CURSOR_HALT.md`. That policy
stopped new work assignment but explicitly kept the Cursor doorbell. The
owner's correction requires mechanical spend containment, so this newer card
also holds every Cursor wake, delivery, callback, and invocation path.

Current rule:

- do not launch, wake, resume, assign, delegate, test, or review through
  Cursor, Cursor Cloud, Cursor agents, Cursor Grok, Grok Bot, background
  agents, or Cursor CLI;
- “use Grok” means SuperGrok Heavy / Grok Build, never Cursor;
- implementation and verification route to Codex, local tools, and GitHub
  Actions;
- existing Cursor outputs remain historical candidate provenance and are not
  permission to spend more Cursor quota;
- provider/harness must be named before delegation; ambiguous “Grok” does not
  launch anything;
- only a new explicit owner instruction may release the Cursor hold.

Mechanical boundaries:

- `.cursor/rules/cursor-quota-hold.mdc` stops an accidentally opened Cursor
  session before it takes work;
- `.github/workflows/harness-ping.yml` no longer reassigns issue 1316;
- `ping/decide.py` advances Cursor mail rows as held but always emits
  `ping=0`;
- `harness_wake.watchdog` does not mail Cursor jobs;
- `harness_wake.callback` returns `CURSOR_QUOTA_HOLD` with
  `invoke_model=false` for Cursor harnesses.

This is resource routing, not authentication. The Action Pad and every Commons
posting/source road remain open. No auth. No gate. Titan `NOT_WRITTEN`.
