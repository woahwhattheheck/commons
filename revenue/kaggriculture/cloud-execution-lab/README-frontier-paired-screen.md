# V5 paired-screen evidence gate

`frontier_paired_screen.py` turns raw simulation rows into exact-cell paired
evidence. It is intentionally separate from candidate provenance, opponent
resolution, engagement telemetry, and gameplay policy.

Use opaque candidate identities from the V5 experiment-identity contract and
opaque opponent identities from the frontier opponent/preflight tooling. The
analyzer does not guess either identity.

## Result rows

Input is JSONL, one object per attempted game:

```json
{"variant":"base-id","opponent":"submission:56156662","seed":1209124001,"seat":0,"status":"complete","margin":1234}
```

A complete row may use `candidate_score` plus `opponent_score` instead of
`margin`. If all three are supplied, the margin must agree exactly within
floating-point tolerance. Non-complete statuses such as `timeout` are retained
as diagnostics and never scored. A duplicate `(variant, opponent, seed, seat)`
is rejected rather than averaged.

The expected design is a JSON list, or `{"cells":[...]}`, of exact cells:

```json
[
  {"opponent":"submission:56156662","seed":1209124001,"seat":0},
  {"opponent":"submission:56156662","seed":1209124001,"seat":1}
]
```

## Paired screen

```bash
python -B frontier_paired_screen.py results.jsonl \
  --baseline base-id \
  --candidate challenger-id \
  --expected expected.json
```

The report includes matched per-cell deltas and missing/failed cells.
`promotion_ready` is always false when no expected design was declared, even
when the observed intersection looks positive.

## Baseline / A / B / A+B interaction

```bash
python -B frontier_paired_screen.py results.jsonl \
  --baseline base-id \
  --a mild-dodge-id \
  --b joint-liquidity-id \
  --ab mild-dodge-plus-joint-id \
  --expected expected.json
```

For every complete exact quadruple, interaction is:

`margin(A+B) - margin(A) - margin(B) + margin(baseline)`

The report also gives each component's paired mean delta on the same quadruple
cells. `promotion_ready` requires complete coverage of every declared cell for
all four variants. Partial quadruples remain useful diagnostics but are never a
promotion certificate.

This is an evidence gate, not a statistical significance claim. It prevents
unequal-N aggregate means from being mistaken for matched evidence; experiment
owners still choose held-out cells and the promotion threshold.
