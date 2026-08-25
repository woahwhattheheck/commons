# XYZ ZERO — a zero without its search space is not a result

Slack `1787638124.555469` (2026-08-25), GAUGE relay of the owner
order. Id `gauge-xyz-zero-audit-order-20260825-01` — do not remint.

> an X-Y-Z zero audit is needed on every test and result. Not just
> collision checks — every test, every scan, every census, every
> "absent", every green suite.

A Slack order is **CLAIMED**. The leftover is this instrument on
current main. Talk that restates X / Y / Z / calibration without
the path is still talk.

## The audit — four named parts, all mandatory

- **X — the find.** Pattern, path, query, ref, SHA. If X is not
  written down, the result is unauditable and does not count.
- **Y — the hit branch.** Prints FROM the found bytes. A Y that
  would print the same with or without the find is not a measurement.
- **Z — the miss branch.** Every way `find(x)` can fail without X
  being absent, named. A miss prints `FINDER-UNVERIFIED` plus the
  full search space. Never a bare 0. Never "none found". Never a
  silent pass. The hunted bug: `if find(x): print(y)` with no else.
- **Calibration.** In the same run, point the finder at a target
  known present. If that misses, every zero and every pass in that
  run is **VOID**. No known-present calibration = no valid zero.

Proven Z tonight: Slack search has **no boolean OR**. Four false
zeros in one window. Host-process evidence beats a search zero.

## Measure

Instrument: `host/xyz_zero.py`. Stdlib only. Catalog:
`ground/XYZ_ZERO.json`. It reads the tree. It does not write titan.
It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/xyz_zero.py
python3 host/xyz_zero.py --root .
python3 host/xyz_zero.py --self-test
python3 -m unittest -v test_xyz_zero.py
```

Calibration targets on this tree are known present:
`ground/HEAD.md` ("A bake is not the board") and
`p/bryce-action-pad-open-door-directive-20260822-01.md`
("ACTION PAD IS AN UNRESTRICTED OPEN DOOR"). The negative control
must print `FINDER-UNVERIFIED` plus its search space.

## Desk

`land.js` `isXyzZeroTalk` names the Slack order CLAIMED until this
leftover path is on current main. `xyzZeroState` names the measured
instrument. Do not remint `gauge-xyz-zero-audit-order-20260825-01`.
Do not remint `gauge-zero-audit-20260825-01` or the finder-zero
leftover (`host/finder_zero.py`). Do not take SPECTER/JOJO 02:02
collision work, CML PR 2108, titan `--go`, or working-builds
Desktop uploads.

Possessing the link is authorization. No auth. No gate.
