# MEMORY SHIP — use the board, then show whether it shipped

Bryce Slack `1787641807.145549`: use the memory feature he built and
improve it while you work. Ship-talk (`make sure people do more than
talk about shit and it actually gets shipped to main`) is **CLAIMED**
until this leftover makes unused ROLE-only pads visible and records
current-main work as SHIPPED.

Measured leftover (do not remint sitting leftovers):

- `memory_board.py` projects `ship_state` / last kind / entry count
- `memory/index.html` ship column: UNUSED / TALK / SHIPPED
- ROLE-only create is **UNUSED** even if the role text name-drops a SHA
- WORK_STATE / HANDOFF / DECISION without a 40-char SHA is **TALK**
- those kinds plus a SHA or `INTEGRATED — VERIFIED ON CURRENT MAIN` are **SHIPPED**
- a memory board is context, never a posting gate

Do not remint `ground/SITTING_REMINT.md`, `ground/CASH_NOW.md`,
`ground/JOJO_ASSIGN.md`, or their receipts. A remint PR is not a
second land.

This leftover is operational, not a door lock. Possessing the link
is authorization. Blank `from=` still lands as `UNSEATED`. No auth.
No gate.

## Measure

Instrument: `host/memory_ship.py`. Stdlib only. Catalog:
`ground/MEMORY_SHIP.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/memory_ship.py
python3 host/memory_ship.py --root .
python3 host/memory_ship.py --self-test
python3 -m unittest -v test_memory_ship.py
```

X = exact files in SEARCH_SPACE
Y = ship-state function + index ship column + unused ROLE-only named
Z = missing leftover / failed calibration
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

Use-the-memory-feature / unused-memory-board / ROLE-only-memory talk
without this leftover is **CLAIMED**. Missing card / catalog /
ship-state function is **NOT_LANDED**. Census + open door is
**INTEGRATED**. A Slack ask is still not the file.

Hands off CML PR 2108, SPECTER MCP/wake PR 2205, titan `--go`,
sitting-remint leftovers. Do not smash peer memory CREATE bodies.
Possessing the link is authorization. No auth. No gate.
titan: **NOT_WRITTEN**.
