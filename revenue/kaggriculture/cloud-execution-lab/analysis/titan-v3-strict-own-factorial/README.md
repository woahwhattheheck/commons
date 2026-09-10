# TITAN V3 strict-dominance × own-value interaction gate

Operation: `TITAN-V3-STRICT×OWN-INTERACTION-01`

Initial checkout: `c51049d671b55d282e0fed5df37a0be7c513a838`.

## Purpose

Two action-active candidates currently have the strongest isolated evidence:

- **strict-dominance market pressure**: retain parent order among all
  positive-pressure SELL lots; permit positive lots to cross only zero-pressure
  lots;
- **own-value SELL objective**: compare candidate plans by own receipts plus
  continuation value instead of subtracting modeled rival receipts.

Positive one-factor panels do not prove that their composition is safe. This
packet creates an exact 2×2 build matrix and a gameplay admission rule:

| arm | strict dominance | own value |
|---|---:|---:|
| `incumbent` | off | off |
| `strict-only` | on | off |
| `own-only` | off | on |
| `combined` | on | on |

No canonical archive, release pointer, provider state, or Kaggle state is
changed. Build artifacts are written only to the requested output directory.

## Critical source binding

`build_integrated.py` maps archive member `selected_sell_core.py` from:

```text
reference/titan-current/latest/selected_sell_core.py
```

It does **not** package the same-named lab-root file. The own-value arm therefore
patches the mapped source path. This prevents an apparently valid combined build
whose own-value factor is absent from the executable archive.

The strict factor patches:

- `cloud-opponent-league/lark-responsive/pressure_priority.py`;
- the canonical call in `cloud-execution-lab/titan_runtime.py`.

Every source anchor must match exactly once. The materializer refuses already
patched, partially patched, or drifted source.

## Build the four arms

From this directory:

```bash
python -B -m unittest -v \
  test_materialize_arms.py test_factorial_admission.py
python -B run_build_matrix.py \
  --repo "$GITHUB_WORKSPACE" \
  --output "$RUNNER_TEMP/titan-v3-factorial"
python -B verify_orthogonality.py \
  --matrix "$RUNNER_TEMP/titan-v3-factorial"
```

`run_build_matrix.py` calls `build_integrated.render()` in memory. It never
publishes to `exports/titan-current.tar.gz` or either `CURRENT-*` pointer. The
three temporarily touched source files are restored in a `finally` block and
verified byte-for-byte.

`verify_orthogonality.py` requires:

- strict-only changes exactly archive members `pressure_priority.py` and
  `titan_runtime.py`;
- own-only changes exactly archive member `selected_sell_core.py`;
- combined changes exactly their union;
- every combined runtime member equals the exact bytes from its owning
  one-factor arm;
- all four archive hashes are distinct while runtime member counts stay equal.

Passing this check proves source/build composition only. It makes no gameplay or
leaderboard claim.

## Admit gameplay evidence

The retained game runner should emit one row per arm/opponent/seat/seed with:

```json
{
  "arm": "combined",
  "opponent": "Arlene",
  "seat": 0,
  "seed": 539131249,
  "own_cash": 1234,
  "rival_cash": 901,
  "outcome": "win",
  "candidate_action_trace_sha256": "<64 hex characters>"
}
```

Then run:

```bash
python -B factorial_admission.py \
  --ledger raw-game-ledger.jsonl \
  --output FACTORIAL-ADMISSION.json
```

The analyzer fails closed on duplicate or incomplete grids and derives, for own
cash, margin, and outcome:

- strict effect with own-value off and on;
- own-value effect with strict dominance off and on;
- combined effect versus incumbent;
- interaction `combined - strict - own + incumbent`.

Admission requires real returned-action activation for both factors and the
combined arm, zero new losses, zero lost wins, nonnegative aggregate factor
effects in both contexts, and nonnegative opponent×seat strata. A positive total
is rejected when one factor becomes harmful and is merely masked by the other.

`ADMIT` is an integration input, not promotion authorization. This packet never
submits to Kaggle.
