# TITAN V3 disabled-feature identity firewall (SOL-NULLSPACE)

This directory turns the V2 weed-continuation regression into a reusable integration boundary. The immediate defect is already owned elsewhere; this artifact prevents the same class from recurring in any optional policy domain.

## What it proves

A disabled feature must be an **identity transform** at every observable surface:

1. exact returned action bytes;
2. producer route and retained planning state across later turns;
3. Python RNG trajectory;
4. source identity of every file the contract audited.

`identity_firewall.py` provides two independent controls:

- a source-bound AST audit that rejects protected calls not dominated by their enable gate; and
- a lockstep dynamic oracle that compares baseline and candidate outputs, state projections, and RNG state over multiple calls.

The helper `disabled_identity_firewall()` is the hard edge for integration: when disabled it returns the exact selected object and does not invoke the optional transform at all.

## Current exact witness

`contract.json` is bound to fresh main `ed65812449a2cd021b0635a60ff9171957f3e386` and the exact Git blobs:

- `spatial_tempo.py` — `edbc423023479dbe2e78131495334384a87b607f`
- `titan_runtime.py` — `b952c9c228ecbde592bf3d2df01638677abb0d24`

The expected red baseline is deliberately explicit:

- no `Features.weed_continuation` field;
- `_continue_weed()` can be called without an owning feature gate;
- `_deliver_idle_fertilizer()` can be called without an idle-fertilizer gate;
- `SpatialTempo` construction and installation are not dominated by any enabled optional spatial domain.

This is not a gameplay or score claim. It is a source-bound architectural regression witness.

## Run

From this directory in a full repository checkout:

```bash
python -m unittest -v test_identity_firewall.py
python identity_firewall.py \
  --root ../.. \
  --contract contract.json \
  --json-out evidence/audit-current.json
```

The second command exits `0` only when the finding set exactly matches the pinned expected red baseline. After the runtime repair lands, re-pin the source blobs, set `expected_current_findings` to the new expected set, and require a clean boundary:

```bash
python identity_firewall.py \
  --root ../.. \
  --contract contract.json \
  --json-out evidence/audit-current.json \
  --require-clean
```

Exit codes are stable for automation:

- `0`: contract matched; clean when `--require-clean` is used;
- `2`: invalid contract, missing file, syntax error, or source-binding mismatch;
- `3`: actual findings differ from the expected set;
- `4`: expected findings matched but the contract is still red under `--require-clean`.

## Integration contract

For every new optional policy component:

1. add its feature field to `Features`;
2. hard-gate construction/installation on the union of domains that can activate it;
3. hard-gate each independently optional sub-transform on its own flag;
4. include route tables, retained obligations/plans, diagnostics with future behavioral effect, and RNG in lockstep projections;
5. prove at least one adversarial stale-state case while the feature is disabled;
6. land the source-bound clean receipt before enabling the feature in a candidate config.

The tests include a stale-state mutation that preserves the current output, specifically to catch “looks identical this turn, diverges later” regressions.

## Scope and custody

This branch is additive analysis/test material only. It does not edit canonical runtime code, candidate configuration, archives, providers, or Kaggle state. The earlier weed-fix owner and T08 retain runtime integration custody.
