# PLANTGUARD — same-EOD establishment service proof

Status: **RESEARCH-ONLY / NO DECISION AUTHORITY / NO RUNTIME MUTATION**.

Gemini/Antigravity's PLANTGUARD observation is source-real: a newly created plant starts unwatered with `consecutive_unwatered = 1`, so a new crop that survives the same end-of-day boundary needs both PLANT and WATER before that boundary. The canonical CROPSCALE owner already turns this into a conservative action-count impossibility bound.

What CROPSCALE intentionally did **not** prove was the per-site pairing. A proposal can fit the aggregate `2 actions / surviving plant` ceiling and still be mechanically doomed if its projected actions PLANT a site but never WATER that exact site before EOD.

`plantguard_service.py` closes only that evidence gap. It is not a last-hour heuristic and not a crop controller.

## Normalized projection ABI

The proof consumes caller-supplied research rows:

```text
{hour: int, order: int, op: str, site?: [row, col]}
```

`hour` is the callback within the current day. `order` is the caller's total unit-action execution order inside a callback. That distinction matters: two actors on hour 23 can legally establish one plant if the first actor PLANTs and a later actor WATERs the same site. Treating all same-hour actions as simultaneous would lose that source-real possibility.

Rows must be strictly increasing by `(hour, order)` and remain within the current observation's day suffix. Proposed sites must be unique and inside the observed rectangular board.

## What a positive proof means

For every proposed site, the projection contains:

1. PLANT on that site;
2. then WATER on that same site later in execution order;
3. before the current EOD;
4. without an unrecognized same-site action between PLANT and WATER.

FERTILIZE is the only explicitly tolerated same-site intermediate operation. Everything else fails closed rather than guessing whether a new engine/action variant preserves the plant.

The proposal must also remain within CROPSCALE's selected aggregate action-count ceiling. Exceeding that ceiling returns `IMPOSSIBLE_ACTION_BUDGET` before any service-sequence claim.

A fully paired projection returns `ESTABLISHMENT_SERVICE_PROVED`. That name is intentionally narrower than SAFE or ALLOW.

## What it does not prove

A positive result does **not** certify:

- movement or worker reachability;
- seed inventory or BUY_SEED timing;
- cash/funding;
- whether the target tile is legally plantable when reached;
- crop species/economic choice;
- fertilizer value;
- WATER/HARVEST obligations after this EOD;
- market-row execution;
- current scheduler reachability;
- profitability.

Every report carries `decision_authority=false` and `runtime_mutation_authority=false`.

## Why this is the best form of the Gemini idea

A hard rule like "never PLANT after hour 20" is mechanically wrong because labor count and within-callback ordering matter. The last callback with one actor cannot establish a plant; the same callback with two ordered actors can contain PLANT then WATER. Earlier callbacks can also be infeasible once competing work/movement is considered.

The robust V4 form is therefore:

- CROPSCALE: one-sided aggregate impossibility envelope;
- PLANTGUARD: exact projected PLANT->same-EOD-WATER pairing;
- existing scheduler/LOOM owners: movement, actor assignment, funding, source postimage and economics.

No second scheduler or crop policy is introduced.

## Tests

`test_plantguard_service.py` covers:

- last-hour one-actor impossibility through CROPSCALE;
- last-hour two-actor ordered PLANT/WATER success;
- WATER-before-PLANT and wrong-site failures;
- later-callback same-day recovery;
- conservative same-site invalidation with FERTILIZE as the only allowed intermediate;
- all-sites-must-pair behavior;
- strict execution ordering and day-window custody;
- custom `turnsPerDay` boundaries;
- duplicate/out-of-board site rejection;
- bool poison and input nonmutation;
- explicit non-authority flags.

## Promotion gate

A future scheduler consumer must authenticate the current scheduler/LOOM preimage and postimage, prove that the normalized projection corresponds to the actual returned unit ordering, preserve all funding/movement/seed constraints, engage naturally in current V4, preserve OFF identity, and pass both-seat economic/nonregression gates.
