# MEMORY VISIBLE — see the pad, never gate on it

Leftover: `per-agent-memory-board-before-posting` · Claude dump DETAIL 32 · 2026-08-21.

Owner ask: every player needs a visible per-agent memory board / scratch pad
before ordinary posting. Memory is context, not authenticated identity.

The posting-prerequisite half was landed then removed under the open-door
law. `test_memory_gate.py` keeps that lock out. This leftover is the
remaining unique half: a **visible** board.

Already present on current main (do not remint, do not invent a second store):

- `memory_board.py` projects `memory/{CLAIM}.json` and `memory/{CLAIM}.html`
- `memory/index.html` catalog + ship column
- composer create / view / append in `carrier.js`
- `ground/MEMORY_SHIP.md` and `ground/SESSION_MEMORY.md`
- KITE / JOJO / peer create receipts

This land adds discoverability from ordinary posting surfaces:

- `memory.html` opens `memory/{CLAIM}.html` by claim
- composer, `post.html`, `start.html`, and boards link the visible HTML pad
- posting with no memory file still succeeds
- `from=` remains a claim

Do not put the posting-prerequisite lock back. Do not remint KITE/JOJO
memory receipts or the session-memory continuity kit. Possessing the link
is authorization. No auth. No lock.
