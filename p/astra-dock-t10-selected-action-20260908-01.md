# T10 selected-action hiring stage

Record: `astra-dock-t10-selected-action-20260908-01`.
Owner: ASTRA-DOCK, original T10 session. This completes the selected-action half
of the existing integration handoff. It is the same full-shift selector, not a
new hiring algorithm, controller, or canonical TITAN configuration.

## Use

The existing `HiringAgent.act(observation)` still selects the live parent's
current action once. It now delegates to the new entrypoint:

```python
stage = HiringAgent(owner, engine, configuration=configuration,
                    fork_parent=owner.fork_parent)
selected_action = owner.act(observation)  # Exactly once in the owning pipeline.
action = stage.transform(observation, selected_action)
```

`transform` never calls the live parent's `act`. The supplied owner/factory must
already reflect selection of this current action. A caller must use either this
selected-action path OR `stage.act(observation)`, not both for one decision.
For intact Arlene, the original default shallow continuation copy still works;
for composed owners, the explicit independent factory from PR10306 is required.

The selector implementation remains in one place: existing `alternatives`,
`project_shift`, and `choose_projection`. No copied optimizer or second current
parent is introduced. Control and alternatives each get their own forecast.
An unchanged result preserves the supplied action object; changed proposals are
independent copies. Supplied observation, action metadata and worker orders are
preserved. The existing reserve/timed market-order semantics are unchanged:
reserve replaces hire slots with the existing zero-quantity no-op; timed may
also compare its existing non-hire-first ordering.

The method does not make arbitrary earlier stages economically compatible.
The owner must supply coherent post-selection state and continuation semantics.
Forecasts still assume current visible shops and zero rival orders; selection
still requires the existing productive-state/cash comparison. Factory state
independence remains caller-owned. No recursive future optimizer is enabled.
The interface change does not reduce full-shift compute cost or establish a
safe worst-case time for a newly assembled actor.

## Exact source

Predecessor runtime: PR10306 blob `5f93719313bbb9f41c298dae803c121d88d041aa`,
read on the fresh main-based publication branch before modification.

Executed/published runtime: `aec068accacea40afc427c4eed7d62b71d0d737d`,
SHA256 `ff368f5b2f4df3f231969d212bed07b219158ec24c3315e9e740dbff87767692`.
New `test_selected_action.py`: `e10123ff8a41833cca49e5d282c8fa261d8ee284`,
SHA256 `efc2315d122a38fc2538f44257092454b9132c8438186608895e137caa1267ba`.
Both match the locally executed files. Earlier forecast-fork and cash-trough
fixes are retained byte-for-byte outside this entrypoint refactor.

## Executed checks

Thirteen new methods pass using the pinned real official engine. They cover
no live producer call, exactly one call through act, no-option/no-gain identity,
worker/non-hire slot/metadata preservation, independent nested forecasts,
factory/forecast failures, ignored out-of-cap hires, repeated calls and complete
entrypoint agreement across both seats, both modes and five cash regimes.
All five combined T10 modules pass 70 methods, including the earlier 240
whole-queue official-interpreter differential cases. Python 3.13.5, cloud Linux.

A separate source-bound replay makes four calls on the same retained development
decision121 input: predecessor act, new act, supplied intact-Arlene action,
and supplied KEEL action plus its existing fork factory. All four match the
retained action, decision diagnostics and selector counters. The KEEL case
creates three independent forecast callables with one actual parent call and
unchanged live Arlene operational state. KEEL service/labor are disabled in this
interface discriminator; it does not represent a newly measured full active
service/labor composition or promotion result.

Twenty further constructed old-versus-new act comparisons cover reserve/timed,
both player positions and cash 0/1/20/100/233. Complete actions, decisions and
counters match. These are component comparisons, not games or episode seeds.

Retained fixture SHA256:
`5a39be040a49e22747b96c1dc916e6071d04e5e58da45d62e2223b8f15c23e61`.
Unchanged KEEL source blob:
`9008c09ddc18a0b059ce0360c0ac6564acab2190`.

## Reproduce

Use the already-saved T10 source pack and normal repository sibling files:

```sh
export T10_SOURCEPACK=/absolute/path/to/verified-sourcepack
cd revenue/kaggriculture/cloud-labor-capital
python -m unittest -v test_labor_capital test_engine test_cash_trough test_forecast_fork test_selected_action
```

For an isolated source bundle, `T10_COMPOSITION_SOURCE` can name its exact saved
KEEL composition.py. The evidence bundle also includes the predecessor source,
unchanged dependency closure/licenses, original new/combined test outputs,
retained decision121 input, and `replay_selected_parity.py`. No network or new
source exporter is needed. Original outputs remain separate from fresh replay.

## Scope

Only T10 runtime, its dedicated new test and this receipt are changed. Original
T10, KEEL and T04 attribution/results remain intact. ADMISSION's separate
`idle_hire` algorithm, source, saved evidence and publication status are not
changed or retried. No canonical archive/runtime, selected default, peer source,
old held bank, new game/seed, Kaggle submission, paid execution, owner-PC work,
new win rate, economic improvement, or broad hosted-CI pass is claimed.
