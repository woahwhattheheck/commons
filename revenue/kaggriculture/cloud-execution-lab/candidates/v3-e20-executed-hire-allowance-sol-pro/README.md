# TITAN V3 — E20 executed-HIRE allowance repair

Operation: `TITAN-V3-E20-EXECUTED-HIRE-ALLOWANCE-REPAIR-20260910-01`

## Exact input

- Slack handoff: `F0C0JPCAAQP` (`v3_candidates_657b3d9c.tar.gz`)
- Bundle SHA-256: `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`
- Source: `overlay/e20_hire_guard.py`
- Source SHA-256: `3d841b271bd735d4edecfc05be31753bd94f5a5fcfb37e0fea24df4eeb7372ea`
- Pinned engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`

## Exact defect

The authenticated one-tree E20 implementation selects the first
`max_hires - hires_today` **raw HIRE rows** and deletes every later HIRE. The
official engine does not increment `hires_today` merely because a row says
`HIRE`; it increments only when that literal-index HIRE can pay its Fibonacci
cost.

A minimal score-facing counterexample is:

```text
money=0, hires_today=2, max_hires=3, farmHandCostMult=1
market=[HIRE, SELL WHEAT 1, HIRE]
```

The first HIRE costs 2 and fails. The SELL then supplies cash. The last HIRE can
now execute and reaches the intended cap of 3. The predecessor keeps the failed
first row, deletes the last row, and ends at 2 hires. That is underfill, not a
cap.

The predecessor also counts and rewrites HIRE rows outside the official
`q[:max(1, maxMarketOrdersPerTurn)]` prefix, creating action churn with no engine
effect.

## Repair

The replacement is deliberately fail-closed:

- It considers only the interpreter-visible market prefix; suffix bytes remain exact.
- At zero remaining allowance it removes every executable HIRE.
- Otherwise it deletes later HIREs only after every allowed earlier HIRE is
  provably funded from current public cash using the exact Fibonacci/multiplier
  cost and before any preceding money-changing market uncertainty.
- An unfunded allowed HIRE or prior BUY/SELL/BUY_LAND ambiguity returns the exact
  original action. No policy guess is made.
- Front-loaded, certainly funded HIRE queues retain the predecessor's intended
  behavior.
- Inputs are not mutated and repeated application is idempotent.

## Evidence

`test_e20_executed_hire_allowance.py` contains ten standard-library contracts:

1. exact predecessor killer for failed HIRE → SELL funding → successful HIRE;
2. preserved behavior for a front-loaded funded allowance;
3. fail-closed preceding money-changing order;
4. only interpreter-visible HIREs dropped at the cap;
5. suffix-only excess is exact identity;
6. exact Fibonacci and `farmHandCostMult` certification;
7. sequential certification of two allowed HIREs;
8. malformed public/config state is identity;
9. high-demand and terminal identity;
10. input nonmutation and idempotence.

Local verification against the exact handoff reproduced predecessor
`dropped_indices=[2]`, applied the replacement only after the source hash
matched, and passed 10/10 contracts. Replacement SHA-256:
`54127c61b25584f76ba75df966d33602d48da8405f4064b6b6ada2f81d5e9074`.

## Scope

This is an additive exact-source repair/evidence carrier. It does not modify the
one-tree publication branch, canonical archive/config/runtime, release pointers,
provider state, Kaggle, or submission state. It makes no strength claim. The
one-tree owner retains integration, rebuild, matched-game panel, merge, and
promotion custody.
