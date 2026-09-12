# Production-v3 postprocessor attribution

This is one bounded screening carrier on the single merged TITAN V5 production-recovery line. It does **not** create another producer tree, flip a default, authorize a release, or submit Kaggle.

## Why this exists

Merged production-v3 archive `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239` repairs the native import seam while preserving 91/92 production-v2 members and the exact gameplay config. Fresh native seed `1209129901` completed against Apex v7 and Arlene v14 in both seats:

- full production-v3 beats submitted V3.1 margin by **+258** against Apex and **+220** against Arlene;
- full production-v3 own score is **-237** versus V3.1 against Apex and **+332** against V3.1 against Arlene;
- full-context `town_procurement=false` loses another 2 Apex / 1 Arlene own-score point and the same margin amount;
- the merged aggregate postprocessor bypass returns exactly to the V3.1 terminal scores on this seed.

The aggregate comparison therefore justifies localization, but the strict champion rule correctly blocks the full candidate on the Apex own-score regression. The goal here is to identify the *stage* responsible before anyone opens single-feature forks.

## Exact baseline authority

- production-v3 archive SHA256: `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`
- `TITAN-CONFIG.json` SHA256: `ba18563683125fd89d5473ddb8a5c3e9431db1787a3046f618a9e03af2cb44af`
- repaired v3 `main.py` SHA256: `b98aec64f83ea9a216def7ab1fef320a6498ae37816f506af1f891c934027035`

The materializer reuses the already-reviewed R04/FrozenSelected semantic pins from the aggregate-survivorship carrier and rotates only the `main.py` identity to production-v3. It authenticates the whole archive before emitting anything. Every treatment changes only `TITAN-CONFIG.json`; the other 91 members remain byte-identical.

## Three valid knockout arms

All arms start from **full production-v3** and keep `consumer=frozen`, `town_procurement=true`, and every unrelated flag unchanged. This is required by the live `Features` contract: redundant-HIRE, idle-fertilizer, and crop-release are only valid on nonterminal frozen composition.

| Arm | Flags turned off | Stage isolated |
|---|---|---|
| `seed_hire_off` | `seed`, `funding`, `redundant_hire` | selected-action seed/funding/hire enrichments after FrozenSelected |
| `inventory_spatial_off` | `operating_stock`, `idle_fertilizer`, `crop_release` | inventory/stock/spatial/fertilizer/crop finalization family |
| `late_market_off` | `market_pressure`, `early_capital` | late market-pressure reorder + early-capital reorder |

`town_procurement` is deliberately absent: native-9901 already measured the full-context town-off singleton. `consumer=parent` is deliberately absent: native-9901 already measured the aggregate bypass, and attempting to combine parent consumer with spatial/redundant flags would violate the production feature contract.

The three knockout key sets are disjoint. They are a stage screen, not an assertion that effects are additive; interaction is explicitly allowed. If none of the three knockouts restores Apex own score while preserving the V3.1 margin gain, stop and treat FrozenSelected transform / cross-stage interaction as the residual rather than manufacturing a finer factorial.

## Materialization

```bash
python -B materialize_stage_knockouts.py \
  --baseline /path/to/production-v3.tar.gz \
  --bundle postprocessor-screen.tar.gz \
  --receipt postprocessor-screen.json
```

The bundle contains `SCREEN.json` and one nested deterministic archive per arm. Publication uses the existing cooperative create-only pair routine, so the bundle and receipt are reserved together and rollback on ordinary collision/write failure.

## Native follow-up

After exact-head source gates are green, run only the three new arms on the already-used seed `1209129901`, Apex v7 + Arlene v14, both seats, with the same official interpreter/engine/opponent identities/RNG/timeouts as `selective-carrot/native-9901`. Reuse the existing V3.1, V4, full production-v3, town-off, and aggregate-bypass controls; do **not** rerun them merely to populate this screen.

Decision rule: prefer a knockout that eliminates the Apex `-237` own-score regression without erasing the positive V3.1 margin delta. If more than one appears useful, widen seeds on the strongest minimal composition before any finer split. A one-seed result is development evidence only and cannot clear the champion/release transaction by itself.

No runtime/default/config pointer/CURRENT/release/Kaggle mutation is authorized by this carrier.
