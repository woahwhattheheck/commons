# IMPACT LEDGER — containment talk is not a land

Slack `1787638509.277739` (2026-08-25), owner P0:

> CLAUDE FALSE-ZERO DEFECT CAUSED DOWNSTREAM DAMAGE …
> Claude’s test/finder logic was `if find(X): return Y`, omitted Z,
> and returned `0` whenever its finder failed.

A Slack alert is **CLAIMED**. The leftover is TRACE CONSUMERS. This
instrument records, for each high-risk consumer: source post/ID/time,
exact named search space X, bytes-derived Y or `FINDER-FAILED`,
explicit Z, downstream row/branch/PR, lane holder, and the repair
that lands.

It does not remint `gauge-zero-audit-20260825-01`. It does not take
finder-zero PR 2175, JOJO `jojo-visual-ci-20260825-01`, SPECTER
MCP/wake, DIO titan `--go`, or CML PR 2108.

## Rule

1. Every result prints X — exact finder, input, path, and ref.
2. Y is derived from found bytes, or the row is `FINDER-FAILED`.
3. Z is the miss branch. Calibration miss or Z prints `FINDER-FAILED`
   plus the full search space, never `0`.
4. Same-run known-present calibration is mandatory. This card uses
   `ground/HEAD.md`.
5. Claude-reported `0` / `none` / `absent` / `no claim` stays
   **QUARANTINED**. Do not build, merge, route, close, dedupe, or
   allocate from it.
6. High-risk first: collision, titan, mcp, device, wake, capacity,
   pr_absence.

## Measure

Instrument: `host/impact_ledger.py`. Stdlib only. Catalog:
`ground/IMPACT_LEDGER.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/impact_ledger.py
python3 host/impact_ledger.py --root .
python3 host/impact_ledger.py --self-test
python3 -m unittest -v test_impact_ledger.py
```

The leftover is **INTEGRATED** when seven high-risk consumers carry
X/Y/Z/owner/repair, the miss branch cannot print 0, and the finder
calibrates against known-present. Talk that restates the alert
without this leftover is **CLAIMED**.

## Desk

`land.js` `isImpactLedgerTalk` names the P0 containment / TRACE
CONSUMERS / Claude-cannot-certify copy CLAIMED until this leftover
path is on current main. `impactLedgerState` names the measured
instrument.

Possessing the link is authorization. No auth. No gate.
