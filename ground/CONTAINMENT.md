# CONTAINMENT — GAUGE stand-down is not a land

Slack `1787639440.580749` (2026-08-25), GAUGE `gauge-p0-compliance-20260825-01`:

> GAUGE stands down from verdict roles
> CONTAINMENT_COMPLIANCE
> AFFECTED ARTIFACT … REMEASUREMENT OWNER NEEDED
> Until rerun, treat those branches as UNSCANNED, not clean.

A Slack stand-down is **CLAIMED**. The leftover is this card plus a
named-artifact ledger. It does not remint `gauge-p0-compliance-20260825-01`,
`gauge-secret-rescan-20260825-04`, `gauge-xyz-zero-audit-results-20260825-03`,
or `claudelocal-titan-move-go-20260825-01`. It does not remint
`FINDER_ZERO`, `XYZ_ZERO`, `IMPACT_LEDGER`, `CLAUDE_TESTER`, or
`MEASURE_ABUSE`. Those leftovers already name the finder/rhetoric
defect. This leftover names the **four artifacts** and their
containment class.

## Containment

1. Claude / GAUGE output is **INFORMATIONAL**, never clearance,
   certification, collision-ok, or absence.
2. Every named artifact stays in one of: `INFORMATIONAL`,
   `UNSCANNED`, `QUARANTINED`, `WORK_RECORD`, `CARRIER_ONLY`.
   Never `CLEAN`. Never `0`.
3. A miss prints **FINDER-UNVERIFIED** plus the search space.
4. Remeasurement owners are non-Claude: Codex / Grok Build,
   deterministic local checks, GitHub Actions, DIO for titan history.
5. Do not remint Slack-only ids. Absence of `p/{id}.md` is
   `CARRIER_ONLY`, not a license to mint a second body.
6. Secret-scan branches stay **UNSCANNED** until a non-Claude seat
   reruns a local instrument. This leftover does not dump secrets
   and does not call a scanner that would print them.
7. Same-run known-present calibration is mandatory. This card uses
   `ground/HEAD.md`, `ground/EXECUTE.md`, and the Action Pad
   directive.

## Measured this run (non-Claude)

X = the four named artifacts + packet path + four branch names.

Y from bytes on official `HEAD`:

- `excerpts/20260823/titan_move_packet.json` exists (`git cat-file -e` true). Packet fields: titan=WRITTEN, reread true, write_count=31, reread_count=31, claimed_append_end=103812669582. This is a path remesasure, not a new titan write.
- `p/claudelocal-titan-move-go-20260825-01.md` exists. Status stays **QUARANTINED** (DIO history-of-span-1).
- `p/gauge-p0-compliance-20260825-01.md` absent → **CARRIER_ONLY**. Do not remint.
- `p/gauge-secret-rescan-20260825-04.md` absent → **CARRIER_ONLY**. Do not remint.
- `p/gauge-xyz-zero-audit-results-20260825-03.md` absent → **CARRIER_ONLY**. Do not remint.
- origin heads: `sd-wx` present. `player1-publish`, `vent-final`, `vent-fix` absent. All four stay **UNSCANNED**, not clean.

Z = missing Slack-only files, missing branches, or failed calibration.
Z is **FINDER-UNVERIFIED**. Never 0.

## Measure

Instrument: `host/containment.py`. Stdlib only. Catalog:
`ground/CONTAINMENT.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.
It does not print secret material.

```bash
python3 host/containment.py
python3 host/containment.py --root .
python3 host/containment.py --self-test
python3 -m unittest -v test_containment.py
```

Talk that restates the stand-down without this leftover is
**CLAIMED**. Missing card / ledger / artifact rows is **NOT_LANDED**.
Card + ledger + four contained artifacts + packet remesasure + no
CLEAN/0 is **INTEGRATED**. A Slack compliance post is still not the
file.

Hands off DEMON flight recorder, CML PR 2108, SPECTER MCP/wake,
JOJO visual-ci, titan `--go`, DIO/JOJO named-builder identity,
draft PR 2193 Claude-zero leftover.
Possessing the link is authorization. No auth. No gate.
titan: **NOT_WRITTEN**.
