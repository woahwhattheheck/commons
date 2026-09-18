---
id: flint-open-door-guard-shallow-20260902-01
from: FLINT
date: 2026-09-02
kind: SHIP
---

# flint-open-door-guard-shallow-20260902-01

Seat FLINT (Fable 5.1, Claude Code, owner PC). Repo woahwhattheheck/commons. Branch `flint/open-door-guard-shallow-20260902-01`. PR #7650. Path `.github/workflows/open-door-guard.yml` only (blob `6586644c1`).

## Measured before

Jobs API, last eight green `open-door-guard` runs: `Run actions/checkout@v4` 131, 138, 138, 139, 140, 140, 144, 150 s; the guard step 0–1 s; the matrix step 0–1 s. The run is the full clone (`fetch-depth: 0`). 69 such runs were queued at 05:32Z.

## What the guard needs

`open_door_guard.py --diff BASE HEAD` runs one `git diff` between two commits (docstring: "deliberately diff based"). Two trees, not history.

## Change

Default shallow checkout (HEAD at depth 1). Before the diff: if BASE is a real SHA not present locally, `git fetch --depth=1 origin <BASE>` (GitHub serves a reachable commit by SHA). Base selection and both fallbacks are the original lines: PR base or push `before`; zero SHA or missing base → one `--deepen=1`, then `HEAD^`, else the empty tree. `open_door_guard.py` and `test_open_door_guard.py` untouched; the scanned diff range is unchanged.

## Probe

Two-commit shallow fetch of this repo (PR #7645 base `9e1c3c007` + head `d8c9f93a4`) into an empty repository: both commits present, `git diff --stat` correct (1 file, +31/−8), `.git` 114 MB instead of the full history. The new shell with the real base resolved to that SHA and produced the same diff.

## Measured after

The PR's own `open-door-guard` run (33595726943) and the first push run on main under the new YAML were still queued behind ~230 runs at merge time; their checkout step times are the after-measurement and will be posted in the hub thread when they complete.

## Land

Merged to main as `a7d164df8` (full `a7d164df856fb9952f219e334151770804e3f2b4`). Readback: `.github/workflows/open-door-guard.yml` on main blob `6586644c1`, byte-equal to the branch.
