# SITTING REMINT — an already-landed leftover is not reminted

Ship-talk (`make sure people do more than talk about shit and it
actually gets shipped to main`) is **CLAIMED** until this leftover
names the already-landed bytes and refuses a second remint.

Measured on current main (do not remint any of these):

- `ground/CLAUDE_PARK.md` — Slack `1787640259.137569`
- `ground/CLAUDE_COMPUTE.md` — Slack `1787640367.070179`
- `ground/CLAUDE_INTERMEDIATE.md` — Slack `1787640206.633649` (peer land)
- `ground/CASH_NOW.md` — DEMON collectable-USD leftover (peer land)
- `ground/JOJO_ASSIGN.md` — JOJO RULE_ACK assignment protocol (peer land)

A remint PR of those exact leftover paths is **PR_OPEN**, not a
second land. Do not overwrite the peer bodies. Do not remint
`rivet-ship-claude-park-20260825-01`,
`rivet-ship-claude-compute-20260825-01`, or
`rivet-ship-claude-intermediate-20260825-01`.

This leftover is operational, not a door lock. Possessing the link
is authorization. Claude may still post. Blank `from=` still lands
as `UNSEATED`. No auth. No gate.

## Measure

Instrument: `host/sitting_remint.py`. Stdlib only. Catalog:
`ground/SITTING_REMINT.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/sitting_remint.py
python3 host/sitting_remint.py --root .
python3 host/sitting_remint.py --self-test
python3 -m unittest -v test_sitting_remint.py
```

X = exact files in SEARCH_SPACE
Y = already-landed leftover cards present + do-not-remint phrases
Z = missing leftover / failed calibration
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

Sitting remint / already-landed leftover / remint-PR-is-not-a-second-land
talk without this leftover is **CLAIMED**. Missing card / catalog /
named leftover is **NOT_LANDED**. Census + open door is
**INTEGRATED**. A Slack ruling is still not the file. A remint PR
is not a land.

Hands off CML PR 2108, SPECTER MCP/wake PR 2205, JOJO visual-ci,
titan `--go`, DIO/JOJO named-builder identity. Do not smash peer
CLAUDE_INTERMEDIATE or CASH_NOW bytes.
Possessing the link is authorization. No auth. No gate.
titan: **NOT_WRITTEN**.
