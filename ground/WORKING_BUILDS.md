# WORKING BUILDS — Slack list is not a land

Slack `1787637681.321149` (2026-08-25), DEMON utilization report:

> MACHINE-ONLY WORKING BUILDS — CLAIM PROVENANCE-FIRST
> INTEGRATION. Three working builds are stranded off Commons:
> (1) `Desktop\rook-resident-native\` package + 9 tests +
> `state/session-run.json` + `evolve.json`. (2)
> `Desktop\MUHL_KEYB\keyb01.mno` 430,860 bytes, SHA prefix
> `a63396...`, depth 8, 16x128, HELP/READ/WRITE/FIRE/SURFACE/ACK.
> (3) `Desktop\MUHL_KITE1_SPIKE\TRAIN_CIRCUITS_FROM_FILE.json`
> 20,076 bytes, 35 Titan circuits, perceptron 200/200,
> hidden-layer 60/60, attention 200/200, transformer 120/120.
> Companion seeker + SmolLM2 Q8 P0 is 386,404,832 bytes.

A Slack list is **CLAIMED**. The leftover is a provenance census
on current main plus one disposition per artifact: integrate,
superseded, or quarantine. It does not upload model or container
bytes. It does not execute WRITE/FIRE/Titan mutations.

## Assigned lanes (not this leftover)

- **DIO / JOJO** — owner-machine hash of the Desktop sources.
- **Rook package tests / checkpoint-resume** — stay on the
  originating machine until the exact bytes are exported.
- **KEYB container write / FIRE** — forbidden until the artifact
  contract and scoped dest are reconciled.
- **Titan census companion model** — do not upload 386MB.

## Measure

Instrument: `host/working_builds.py`. Stdlib only. Catalog:
`ground/WORKING_BUILDS.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/working_builds.py
python3 host/working_builds.py --root .
python3 host/working_builds.py --self-test
python3 -m unittest -v test_working_builds.py
```

The leftover is **INTEGRATED** when all three artifacts have a
named disposition. STRANDED / QUARANTINE / SUPERSEDED on an item
means those Desktop bytes are still not shipped. Talk that lists
the three builds without this leftover is **CLAIMED**.

## Dispositions on this tree

- **rook** — QUARANTINE. No `rook-resident-native` path. Freshest
  canonical equivalent: `muhl/containers/MUHLNICKEL_ROOKERY/RESUME.md`.
- **keyb** — QUARANTINE the 430,860-byte container. Manifest
  `excerpts/20260821/keyb01.manifest.json` already names SHA
  `a63396b59b0fb9f0…` plus the mouths. Fab `--check` refuse-closes
  on the public `[local]` dest. Do not upload `keyb01.mno`.
- **titan census** — SUPERSEDED for the four named scores by
  `p/p1-train-subzero-surface-20260818-01.md`. Exact JSON name
  stays absent. 386MB companion stays QUARANTINE.

## Desk

`land.js` `isWorkingBuildTalk` names the machine-only /
rook-resident-native / keyb01.mno / TRAIN_CIRCUITS_FROM_FILE copy
CLAIMED until this leftover path is on current main.
`workingBuildState` names the measured instrument.

Possessing the link is authorization. No auth. No gate.
