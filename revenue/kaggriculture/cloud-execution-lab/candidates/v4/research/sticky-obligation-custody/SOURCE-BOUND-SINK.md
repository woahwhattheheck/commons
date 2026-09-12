# STICKY source-bound sink evidence

This is the source-authority closure for the CARRY half of `sticky-obligation-custody`.

The incumbent `sticky_obligation.prove_carry_consumption()` deliberately refused to infer inventory consumption from action syntax, but its replacement evidence fields (`consumption_authenticated`, `consumed_item`, `consumed_units`) were still ordinary caller data. A caller could therefore mark a source-real no-op as a consuming sink. The decisive example is a second same-animal same-day `FEED`: the official engine returns immediately when `fed_today` is already true, yet the old row vocabulary could still assert one consumed WHEAT.

`source_bound_sink.py` removes that assertion seam without widening gameplay policy.

## Authority

The producer captures and authenticates the exact official engine Git blob `3c202c7ee921da239356789e266b694635103fc4` and engine-spec blob `b354d06b742fe48402513792253f1a5c29366b20`. It additionally source-checks the exact FEED/FERTILIZE semantic anchors and the standard `turnsPerDay=24` contract. The sibling sticky proof is captured and authenticated at Git blob `41b887cb96fe684522a1f19124cf4b0377207a9c` before its obligation/burden helpers are used.

The source-bound producer accepts normalized projected **pre-state** (`actor`, callback `step`, action `op`, tile, carried units) and derives the effect itself:

- `FEED` consumes one WHEAT only when the tile contains an animal, `fed_today` is literal false, and the actor has at least one WHEAT;
- `FERTILIZE` consumes one FERTILIZER only when the tile is a plant and the actor has at least one FERTILIZER. Existing fertilization duration does **not** make the action a consumption no-op; the official source still takes inventory before applying `max(existing, day+2)`.

The result is an immutable, non-serializable in-process `SinkTransitionEvidence` capability registered by the producer. It is bound to exact actor/step/op/item, official source identities, and before/after state digests. A plain mapping with matching-looking fields is rejected.

## Consumer

`prove_carry_consumption_source_bound()` preserves the incumbent CARRY rules for:

- actor-local same-day custody;
- existing carried inventory consuming sink capacity first;
- later PICKUP / COLLECT_FERTILIZER increasing burden;
- DROP failing closed;
- WHEAT HARVEST failing closed as unknown acquisition;
- duplicate obligated-actor callback rows failing closed.

A FEED/FERTILIZE row contributes sink capacity **only** through `row["sink_transition"]` containing producer-issued evidence for that exact row. Legacy caller fields `consumption_authenticated`, `consumed_item`, and `consumed_units` are ignored and have zero positive authority.

This does not claim that a caller's projected pre-state is authentic. Projection/postimage custody remains an upstream prerequisite. The closure is narrower and source-real: given an authenticated projected pre-state, the caller can no longer manufacture the engine effect by assertion.

## Run

From this package directory:

```bash
python -B -m unittest -v test_source_bound_sink.py
python -O -B -m unittest -v test_source_bound_sink.py
python -m py_compile source_bound_sink.py test_source_bound_sink.py
```

The focused suite covers official source authentication, positive FEED/FERTILIZE consumption, second-FEED no-op, empty-inventory/non-plant no-ops, already-fertilized-but-still-consuming semantics, legacy assertion impotence, forged capability rejection, exact actor/step binding, incumbent competing-inventory burden, and DROP/HARVEST fail-closed boundaries.

## Boundaries

Research only. No gameplay/runtime/default/config/composer/COMPOSITION/INTEGRATION/archive/Kaggle activation is changed. This is a same-package proof producer/consumer surface for downstream CARRY work; it is not a new controller or a second V4.
