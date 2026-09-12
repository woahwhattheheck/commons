# Replay loss autopsy

Deterministic, stdlib-only research tooling for extracting one exact Kaggriculture replay episode from `farmer_actions.csv`, `market_orders.csv`, and `matches_meta.csv`.

The tool is intentionally descriptive rather than causal. It reports only fields present in the source CSVs: exact metadata rows, per-player/day action and market summaries, source hashes, resolved column names, and a chronological final-callback event tail. It does not infer cash, tile state, inventory, opponent identity, economic value, or which policy mechanism caused a result.

## Run

```bash
python extract_episode.py \
  --farmer-actions /path/to/farmer_actions.csv \
  --market-orders /path/to/market_orders.csv \
  --matches-meta /path/to/matches_meta.csv \
  --episode 108020335 \
  --tail-callbacks 96 \
  --output episode-108020335.json
```

Common column names are resolved through a small alias table. If the dataset contains multiple plausible columns for the same semantic field, the tool fails closed instead of guessing. Supply an explicit JSON mapping with `--schema-json`:

```json
{
  "farmer_actions": {"episode": "episode_id", "player": "seat", "step": "step", "verb": "action_verb", "target": "target", "qty": "qty"},
  "market_orders": {"episode": "episode_id", "player": "seat", "step": "step", "verb": "order_verb", "item": "item", "qty": "qty"},
  "matches_meta": {"episode": "episode_id"}
}
```

Every output records SHA-256 and byte length for all three inputs plus the exact resolved columns, so a downstream FIELD-MINE or loss-analysis owner can bind conclusions to source bytes rather than Slack prose.

## Cross-episode recurrence

Once multiple episodes have been extracted from the same raw CSV snapshot, `compare_episode_extracts.py` can report exact descriptive action, market, and relative-tail tokens that recur across them:

```bash
python compare_episode_extracts.py \
  episode-108071852.json \
  episode-108073260.json \
  episode-108073343.json \
  --min-episodes 2 \
  --output recurrent-loss-signatures.json
```

The comparator fails closed unless every extract has the canonical `titan.v4.replay-loss-autopsy.v1` schema and binds identical SHA-256 plus byte lengths for all three raw CSV inputs. Duplicate episode IDs, duplicate JSON keys, malformed source identities, boolean-as-integer fields, and malformed summary/tail rows are rejected. Tail recurrence is normalized only by relative callback offset from each extract's reported `max_step`; it does not claim equivalent game state.

Recurring tokens are routing evidence only. They can tell a downstream owner that the same descriptive pattern appears across multiple source-bound episodes, but they are not causal evidence and do not imply that changing the repeated action or market row would improve score.

## Fail-closed rules

- duplicate headers and malformed short/long CSV rows are rejected;
- ambiguous required aliases are rejected unless explicitly mapped;
- step and quantity parsing accepts strict integer text only, with no float/bool coercion;
- an episode absent from all three tables is an error;
- invalid tail/day parameters are errors;
- unknown or non-integer quantities remain visible through `qty_raw` and are excluded from `explicit_qty_sum` rather than coerced;
- multi-loss recurrence requires identical authenticated raw-source snapshots across every compared episode.

## Validation

`test_extract_episode.py` is self-contained and uses temporary synthetic CSVs. It covers deterministic output, exact metadata preservation, explicit schema disambiguation, absent episodes, malformed rows, and invalid parameters in normal and optimized Python.

`test_compare_episode_extracts.py` covers source-snapshot mismatch rejection, duplicate episode and duplicate-key rejection, strict integer handling, deterministic CLI output, relative-tail recurrence, and configurable recurrence thresholds in normal and optimized Python.

This package is research-only. It does not modify Titan gameplay, configuration, defaults, production runtime, submissions, or Kaggle state.
