# CLAUDE ZERO — retract Claude-reported zeros; never print silent 0

Slack `1787638427.993939` (2026-08-25), DEMON `OWNER_RULE_CORRECTION`:

> every zero reported by Claude was wrong. This is proven instrument
> failure, not merely uncertainty.

Exact failure shape:

```
if find(X): return Y
```

with no audited Z/miss branch. When the finder failed — wrong query
semantics, stale/ref/path/input/truncation/permission/encoding/other
unenumerated cause — it returned `0`. The zero described the broken
finder, not the world.

A checklist of miss modes is not enough. Z can be anything not
anticipated. Same-run known-present calibration and full search-space
disclosure are mandatory.

Peer leftover `host/finder_zero.py` (GAUGE Slack `1787638031.533189`)
already ships the general miss-branch rule. Do not remint it. This
leftover is the Claude retract: re-run the original search spaces
with a non-Claude instrument.

## Classification

- **RETRACT** every Claude-reported zero. Do not cite it as absence,
  clearance, capacity, count, pass, or a usable lower bound.
- Re-run the original search space with a **non-Claude** instrument
  and a receipt: X exact input/pattern/ref, Y sourced from found
  bytes, Z explicit `FINDER-FAILED` / `FINDER-UNVERIFIED`, full search
  space, known-present calibration in the same run.
- Claude is not a tester/verifier. Claude output may stay
  implementation evidence. No positive, zero, green, or red Claude
  test result is a verdict.
- A replacement finder must not silently emit zero. Calibration fail
  or Z reached → print `FINDER-FAILED` / `FINDER-UNVERIFIED` plus the
  full search space, never `0`.

Preserve history. Do not overwrite the bad result. DIO + JOJO append
corrections to receipts that consumed a Claude zero. This leftover
does not take that append lane.

## Measure

Instrument: `host/claude_zero.py`. Stdlib only. It reads
`ground/CLAUDE_ZERO.json`, runs the four known-present calibrators in
the same run, and re-searches the four-byte `GGUF` magic that Claude's
six-character scanner could not see. It does not write posts. It does
not add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/claude_zero.py
python3 host/claude_zero.py --root .
python3 host/claude_zero.py --self-test
python3 -m unittest -v test_claude_zero.py
```

Claude-reported-zeros / RETRACT-DO-NOT-DOWNGRADE / FINDER-FAILED /
if-find(X)-return-Y / Claude-no-longer-a-tester talk without this
leftover is **CLAIMED**. Missing instrument or failed calibration is
**NOT_LANDED**. Calibrators found and retracted claims named is
**INTEGRATED**. A Slack correction is still not the file.

Hands off GAUGE `finder_zero`, Claude-tester leftover,
impact-ledger leftover, xyz-zero leftover already on main, DIO/JOJO
receipt appends, titan `--go`, organs 1–31 remint, the cairn/bryce
zero posts, CML 2108. Possessing the link is authorization.
