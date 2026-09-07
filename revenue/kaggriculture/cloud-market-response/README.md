# T12: causal public-history market response

**Experimental callable and reusable predictor. Not promoted over frozen SELL.**
The response mechanism preserves all held wins, but it makes no held action
changes and loses four margin units in two development cases. See RESULTS.md
for all versions, negative cases and the forecasting-versus-decision distinction.

## Runtime interfaces

```python
from policy import ResponsePolicy
research_actor = ResponsePolicy()           # one per actor/match
response_action = research_actor.act(observation, configuration)
control_actor = ResponsePolicy(enabled=False)  # unchanged frozen SELL optimizer
```

`FlowHistory.add(FlowInterval(...))` consumes completed public-observation
intervals. `window_prediction(product, now, end)` returns complete same-phase
historical windows with training timestamps and empirical total-sale ranges.
`scenarios(...)` keeps batch timing, finite hypothetical stock and relative
order uncertainty. No weights are presented as calibrated probabilities.

Live identification uses SORREL's unchanged interval adapter. The policy reads
only its permitted observation and its own previous receipts, never the rival's
private stock, environment seed, future shop draw or recorded future action.
WHEAT/FERTILIZER buy/sell ambiguity is excluded from the learned premium-sale
policy. At the price floor, paying sale counts differ from inventory admissions:
censored evidence is retained, not trained as exact zero.

The optimizer augments the completed incumbent SELL plan. It does not compare
against only the weaker raw Arlene tape. Original rival stress cases remain in
the vector, all candidate scenarios must be nonnegative, and the worst learned
history delta must be positive. Conditional stock starts from at most one
hypothetical shed; no future production is silently invented. A selected plan
is independently replayed through SORREL's exact paired scorer.

The scheduler calls Arlene once, preserves its unit routes and non-SELL order
indices, and retains the seller's cash, input, slot and shed-capacity logic.
This module owns only cloud-market-response; peer directories are unchanged.

## File-agent packaging

The official raw-file entrypoint is **main.py**, not policy.py. The official
loader executes raw source without `__file__`; main.py waits for first call and
uses its provided `__raw_path__`, or normal module `__file__` when imported.

```sh
python -B build.py --output /absolute/cloud/path/t12-response-agent.tar.gz
mkdir /absolute/cloud/path/relocated-agent
tar -xzf /absolute/cloud/path/t12-response-agent.tar.gz -C /absolute/cloud/path/relocated-agent
```

The archive has a root main.py, the original relative dependency layout, a
SHA-256 SOURCE-MANIFEST.json, and retained licenses/notices. No evaluator,
engine, rival perturbation, game seed, trace or evaluation-only truth ships in
this agent. The archive completed a real isolated 719-decision replication
from a different directory with the same final scores.

The sibling `../cloud-titan-composition/vendor/sell/` is required for repository
execution. Its scheduler SHA-256 is
`32c8610c9827d1686a6f831e2c4b6af4c00d32d2aa04dcf25699d976d6d97dd9`.
Build from the pinned sibling source in FREEZE.json; no silent upstream update.

## Reproduce the checks

Run in this directory in a Linux cloud environment with Python 3.10+ and a
C++17 compiler. The existing shared evaluator/official loader and source pack
must be present in their original sibling paths. No package installation,
provider request, new workflow dispatch or credential is performed by these
scripts. The original Apex native module is built from its retained source:

```sh
(cd ../cloud-frontier-policy/next-panel/vendor/apex && \
 g++ -O3 -std=c++17 -Wall -Wextra -pedantic -shared -fPIC -Isource/include \
 -o agent.so source/policy.cpp submission_bridge.cpp)
python -B -m unittest -v test_response.py
python -B engine_cases.py --engine-dir /absolute/cloud/path/engine --output /absolute/cloud/path/market-cases.json
python -B panel.py --seeds 9840001,9840019,9840037 --opponents arlene,apex \
 --engine-dir /absolute/cloud/path/engine --output /absolute/cloud/path/dev-intact
python -B panel.py --seeds 9840001,9840019,9840037 \
 --opponents arlene:sale_cadence,apex:crop_demand,arlene:labor_cadence \
 --engine-dir /absolute/cloud/path/engine --output /absolute/cloud/path/dev-stress
python -B panel.py --freeze FREEZE.json --seeds 9840101,9840119 \
 --opponents arlene,apex,arlene:sale_cadence,apex:crop_demand,arlene:labor_cadence \
 --engine-dir /absolute/cloud/path/engine --output /absolute/cloud/path/held-replication
python -B protocol.py --engine-dir /absolute/cloud/path/engine \
 --expected-dir /absolute/cloud/path/dev-intact --output /absolute/cloud/path/protocol.json
```

These held seeds have already been consumed. Every later use is a replication,
not a fresh holdout. panel.py checks the files listed in FREEZE.json before and
after the panel and rejects existing result filenames. This is a listed-source
freeze, not an assertion that no unrelated file was added to the repository.
FREEZE.json is the immutable pre-run snapshot from 19:59:11 UTC on September 7,
2026; its `held_started: false` records that moment, not the current run status.
The freeze was saved locally before held execution. Do not infer delivery of
any Slack message from this file.

## Provenance and interpretation

Engine: Kaggle/kaggle-environments commit
28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c; exact engine hashes are in every game
record. Existing read-only transport artifacts10030763484 (source) and
10005621438 (engine) were reused; no new transport workflow was launched.
The source pack was an older pinned checkpoint; the selected seller's actual
runtime bytes match the explicit source pin above.

SORREL adapter: Commons0a1f0ec35e903c4b6052681ecf976705a29ab902,
`cloud-frontier-decision/execution/scenarios/adapter.py`, byte-exact Apache-2.0.
FLOW stress variants: Commons41ea491dd130b206b3402f33e1aff356c837aa99,
`cloud-opponent-league/variants.py`, byte-exact evaluation-only reuse. This is
not a claim that FLOW's separate league panels were published or complete.
The legacy SORREL timeline comparison uses the offered MIT licensing option.
See NOTICE and all retained dependency licenses for exact attribution.

All 162 primary games, the five process replications, unit checks and engine
cases are cloud-local results. There is no Kaggle submission, external rating,
bounty award, sponsor acceptance or payment claim. There are only two held
environment seeds; seats and opponent variants are correlated. More accurate
historical flow prediction did not establish a stronger decision policy.
