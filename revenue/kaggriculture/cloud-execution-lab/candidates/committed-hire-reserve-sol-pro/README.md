# TITAN V3 committed-HIRE reserve candidate (SOL-PRO)

## Result

Episode `107130860` exposes a narrow opening-capital regression, not a generic unit-route failure. The action selected from observation step 1 changes from the V1 predecessor queue (`SELL WHEAT 8`, no MELON prebuy) to the V2 queue (`SELL WHEAT 9`, `BUY_SEED MELON 12`). The added seed bundle captures `$960` immediately. Both tapes nevertheless realize the same 12 MELON and 7 WHEAT plant requests before the next-day HIRE boundary and have equal noncash state through observations 19–24. Cash at observation 24 is V1/V2 `$42/$6`; four HIREs cost `$7`, so V2 completes only three and leaves 23 represented fourth-hand rows unbound.

Selling one of the three WHEAT units at the HIRE turn is not a repair: those three units are the exact represented three-FEED input chain. This candidate instead guards the earlier acquisition boundary.

## Candidate

`protect_committed_hire_seed_boundary` is a fail-closed paired-action admission guard. It chooses the supplied predecessor only when the opening queues straddle the 10-slot boundary and the candidate is byte-equivalent except for exactly two edits:

1. one existing SELL quantity increases by exactly one unit; and
2. one positive BUY_SEED row is inserted.

The inserted seed bundle must equal every literal request for that crop before the next-day HIRE row, with zero post-unit stock and no predecessor purchase of that crop. The route must then prove a full day of exact worker cardinality: HIRE-only acquisition at the day boundary, exactly that many hand slots on all 23 represented rows, productive use of every slot, and a following-day HIRE boundary. Route switches, malformed rows, unsupported queues, extra edits, partial prefixes, existing stock, and all non-opening steps return the candidate unchanged.

The module calls no producer, reads no rival state, predicts no receipt, launches no game, and mutates no canonical source/config/archive/pointer.

## Acceptance evidence

Run from this directory:

```bash
python -m unittest -v test_committed_hire_reserve.py
python probe_current_route.py
```

The unit suite covers the exact 12-seed / four-HIRE / 23-row witness and unchanged-action predecessors for absent trailing demand, route switch, incomplete prefix bundle, existing seed stock, second market edits, non-unit SELL deltas, unit changes, malformed actor rows, unsupported operations, non-opening steps, input immutability, and deterministic output.

`probe_current_route.py` decodes the landed frozen route, applies the compact replay action pair to that current route, and requires the exact 12-plant / four-HIRE / 23-row structural witness. It does not call the agent or environment.

## Truth boundary

This is a candidate-side causal repair and exact static admission proof. It does **not** claim a counterfactual score, paired-engine acceptance, promotion, merge, archive replacement, Kaggle upload, or win. Those require the repository's matched-engine and release gates.
