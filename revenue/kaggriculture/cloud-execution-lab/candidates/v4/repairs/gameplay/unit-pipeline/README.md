# TITAN V4 UNITPIPE

Status: **source-bound, default OFF; current-native natural engagement/economics pending**.

UNITPIPE isolates one official-engine fact that is easy to miss when reasoning about a returned unit vector as if its rows were simultaneous: they are not. After the engine performs its whole-vector atomic PLANT seed-collateral check, it applies the main farmer first and then each hand in index order, mutating shared farm/private state after every actor. Only after every unit row has executed does the market phase begin.

Official engine authority: Git blob `3c202c7ee921da239356789e266b694635103fc4` at `reference/engine/kaggriculture.py`.

## Why this can matter

Two or more already co-located units can therefore form a legal same-callback state-transition chain. The narrow source helper here only recognizes chains whose rows already exist in the selected action and whose operations do not depend on actor-local inventory:

- empty tile: `PLANT -> WATER`;
- observed `WEED`, empty `COOP`, or empty `PASTURE`: `DIG -> PLANT [-> WATER]`.

A poorly ordered vector can otherwise spend the earlier row as a no-op and create the prerequisite only later in the same callback. `unit_pipeline.py` may reorder those existing pure rows into causal order. It never invents a row, adds an actor, moves an actor, changes a market row, changes crop identity/quantity, or credits a later market purchase/HIRE to the earlier unit phase.

The broader source mechanism also permits an **already correctly ordered** three-actor annual relay on one mature WHEAT/CARROT/MELON tile: `HARVEST -> PLANT -> WATER`. The first actor removes the mature annual and receives its yield, the second consumes a pre-existing seed into the newly empty tile, and the third waters that replacement before end-of-day refresh. `test_annual_relay_witness.py` executes all 3x3 annual old->new crop pairs against the exact engine and proves the reversed `HARVEST -> WATER -> PLANT` control becomes WEED at end of day.

That relay is witness-only here. `HARVEST` deposits product into the executing actor's private inventory, so moving a HARVEST row between actor slots can change cargo custody and later shed-overflow ordering even when the shared tile transition would succeed. UNITPIPE therefore continues to refuse HARVEST-bearing groups until a separate custody proof exists.

## Fail-closed boundaries

The helper is deliberately narrower than the mechanism itself. It refuses any group containing movement, `PICKUP`, `PLACE`, `DROP`, `FEED`, `CARE`, `HARVEST`, `FERTILIZE`, fertilizer collection, malformed rows, ambiguous positions, destructive tile states, or insufficient observed seed collateral. It also consumes the official engine's global same-crop PLANT rule: if raw PLANT demand for the crop exceeds the currently observed seed inventory anywhere in the vector, no local pipeline engages.

OFF is exact action identity. ON preserves the raw PLANT multiset, actor vector length/order, all market rows, and all unrelated action keys. The source packet has no production `Features` wiring, no controller authority, and no promotion authority.

## Validation

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest -v test_unit_pipeline.py test_annual_relay_witness.py
PYTHONDONTWRITEBYTECODE=1 python -OB -m unittest -v test_unit_pipeline.py test_annual_relay_witness.py
python -B -m py_compile unit_pipeline.py test_unit_pipeline.py test_annual_relay_witness.py
```

The tests source-pin the official engine and execute constructed rows through its real `_apply_unit_action` implementation. In particular they demonstrate that an out-of-order `WATER, PLANT STRAWBERRY` leaves the newly planted crop unwatered, while the same existing rows reordered `PLANT, WATER` leave it watered; that `WATER, PLANT TOMATO, DIG` on a weed ends empty while `DIG, PLANT TOMATO, WATER` ends as a live watered crop; and that the mature annual relay works only in causal actor order without granting the helper authority to reorder HARVEST custody.

## Remaining acceptance boundary

Do not activate from constructed witnesses. The next consumer should place this helper at the final current-native returned-unit boundary in a test-only carrier, count natural `eligible_groups` and `changed_groups` across both seats, retain exact baseline/candidate action and state traces, and measure action/cash/margin effects. Annual HARVEST relays additionally require explicit actor-inventory/shed-capacity/EOD-custody accounting before any executable reordering is considered. Zero natural engagement means **COLD**, not disproven. Any production/default/archive/Kaggle change requires a separate evidence-backed decision through the single V4 composition/native assembly path.
