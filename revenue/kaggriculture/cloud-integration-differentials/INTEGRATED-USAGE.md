# Optional integrated funded-seed candidate

This binds CEDAR's existing `seed_funding.py` selector (PR10000) into the actual
`cloud-execution-lab/integrated_selected.py` agent (PR9997). It adds neither a new
funding model nor another producer. The frozen selected policy and exported
PR9997 archive are unchanged. Source availability is not a whole-game result.

## Run from a repository checkout

```python
import sys
sys.path.insert(0, 'revenue/kaggriculture/cloud-integration-differentials')
from funded_main import make_agent

candidate = make_agent()                 # funding selector enabled
control = make_agent(funded=False)       # original integrated behavior
# Keep one instance per actor/match; do not share producer state between arms.
action = candidate.act(observation, configuration)
```

`funded_main.py` also exposes the usual `agent(observation, configuration=None)`
file-agent entrypoint, resetting its instance at step zero. It expects the normal
repository layout with the sibling `cloud-execution-lab` runtime and its pinned
reference files. This file alone is not a self-contained submission archive.

To reuse an existing production instance, pass `production=existing_production`.
Call either the returned object's `act` once, or call that producer once and pass
its selected action to the object's `transform`; do not do both for one turn.
The factory accepts the existing `seed`, `committed`, `sell`, and `horizon`
configuration. `sell=False` retains the same optional seed stage while disabling
the existing seller. `funded=False` removes this optional selector, not the
original seed stage.

## Exact integration boundary

The existing selected-action PLANT check and ALDER route-demand calculation run
first, after the current unit stage. Only a demand-valid reduction followed by
an economic order reaches the new optional callback. The callback receives:

```python
seeded, report = seed_queue_selector(
    mechanics, post_unit_observation, selected, proposed, configuration)
```

The state, selected action and proposal are detached copies. The callback contract
is a seed-only action and a report dictionary; `funded_main` supplies the existing
`select_seed_queue` directly. No seed demand, worker route, projection engine or
market simulator is reimplemented. The resulting queue is fed into the same
continuation projection, committed-arrival snapshot and ordered seller that
already consume the ordinary seed-reduced action.

When CEDAR certifies the complete original fixed-price queue from observed cash
without relying on sale proceeds, `seed_reason` is `funded_economic_order`.
Otherwise its original-action fallback retains `later_economic_order`.
`diagnostics['seed_funding']` contains the complete current-market report only
when the optional callback ran. No callback, `seed=False`, demand rejection, and
nondependent queues retain their previous branch behavior. Existing transform
error handling and explicit caller fallback remain in effect.

CEDAR's certificate preserves non-seed execution for the same chosen rival queue
in the current market phase. It does not prove unchanged later controller choices,
terminal cash, independent game wins, or calibrated rival probabilities. Positive
BUY_PRODUCT requests keep the existing unresolved/fallback path. A newly affordable
HIRE in an underfunded original queue remains a rejected seed edit.

## Evidence and next consumer

CEDAR's original component evidence is retained in this directory without edits:
15 test methods and 71 paired official-market cases. These are inputs to this
join, not new tests or full games from this integration. CYPRESS owns the new
joined integration cases against this same source; their execution receipt must
be read separately rather than inferred from the component result.

T08 and the existing executor can freeze this optional candidate against
`make_agent(funded=False)` on a separately assigned development shard. That
comparison isolates the funding selector; frozen selected SELL remains a distinct
benchmark. No game seeds, held results, selected default, or upload are changed
by this source delivery.
