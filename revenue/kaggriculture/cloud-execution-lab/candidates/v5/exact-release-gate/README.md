# TITAN V5 exact release-gate reducer

Operation: `TITAN-V5-EXACT-RELEASE-GATE-REDUCER-Z17-20260913`

This additive tool reduces the F24-F29 superiority evidence for the exact held WF1+C02 candidate. It does **not** run games, remint candidate bytes, move `CURRENT`/default/release pointers, or submit to Kaggle.

Pinned identities:

- candidate: `8b4b074012fe3bd731c218a4956f85ce8dadd74d5afe81a3e04c2795a2a533ee`
- V3.1 control: `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`
- engine: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`

## Input contract

`reduce_gate.py` consumes one normalized JSON bundle with schema `titan.v5.exact-release-gate.v1`. The bundle must name exactly F24-F29 in `required_lane_cell_counts`; observed cell counts must match those declared counts exactly. Every cell binds a unique lane/fixture/opponent/seat tuple and carries candidate and V3.1 outcomes with status, own/rival score, max callback milliseconds, and fallback count.

The reducer rejects unknown/missing fields, non-built-in scalar types, duplicate cell IDs, duplicate semantic cells, bad package/control/engine identities, missing lanes, or incomplete lane counts.

## Machine gate

The machine-decidable gate holds on any non-success/DQ/timeout/fallback row, non-positive global paired mean, non-positive global paired median, or when win-to-loss conversions exceed loss-to-win conversions.

The report includes:

- all-cell count and F24-F29 lane counts;
- candidate W/L/T;
- paired delta mean, median, nearest-rank p10, and worst;
- positive/zero/negative counts;
- loss-to-win and win-to-loss conversions;
- family, seat, and lane strata;
- maximum callback time;
- deterministic report SHA-256.

## Root-review ceiling

Bryce's release order also contains deliberately judgmental predicates: no negative opponent-family median **with adequate n**, lower-tail behavior materially unlike V4, and no unexplained catastrophic regression. This reducer does not let an evidence producer self-mint those judgments. A clean numeric result is therefore `machine_status=PASS` but `release_status=AWAIT_ROOT_REVIEW`. Root retains the only release/submission authority.

## Test

```bash
python -m unittest -v revenue/kaggriculture/cloud-execution-lab/candidates/v5/exact-release-gate/test_reduce_gate.py
```

The hostile suite covers identity drift, missing lane coverage, semantic duplicates, timeout/fallback rows, negative mean, adverse W->L conversion balance, strict integer typing, strata reporting, and deterministic report hashing.
