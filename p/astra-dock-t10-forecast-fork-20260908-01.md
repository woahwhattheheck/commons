# T10 explicit forecast continuation

Record: `astra-dock-t10-forecast-fork-20260908-01`.
Owner: ASTRA-DOCK, original T10 session. This is a composition extension, not a
new portfolio policy or a defect claim against the accepted intact-Arlene path.

## Interface

`project_shift` and `HiringAgent` now accept the optional keyword `fork_parent`.
Its contract matches the existing T04/KEEL interface: a zero-argument factory
returns a callable taking one observation. Each factory invocation must produce
independent mutable forecast state, captured AFTER the current parent action.
The returned function owns its configuration and bounded continuation choice.

```python
# The owning runtime has selected its current action exactly once.
selected = owner.act(observation)
projection = project_shift(
    engine, observation, owner, selected, configuration,
    fork_parent=owner.fork_parent,
)
```

The current `selected` action is used directly, not recomputed through the
continuation. Alternatively, a runtime may let T10 own the one current call:

```python
hiring = HiringAgent(
    owner, engine, configuration=configuration,
    fork_parent=owner.fork_parent,
)
action = hiring.act(observation)  # Do not call owner separately for this action.
```

The control and each alternative get a separate factory invocation. When no
hire alternatives exist, HiringAgent does not create speculative continuations.
Omitting the keyword retains the original Arlene-specific shallow-copy path.
The optional keyword does not turn that default into a general nested-state copy.

Factory and forecast exceptions propagate. Invalid noncallable factories or
results produce TypeError; no failed custom fork silently falls back to shallow
copy. The factory implementation is responsible for independent state: the API
does not prove arbitrary deep alias freedom or repair a badly written factory.
A deliberate diagnostic counter, such as KEEL's `forks`, may record factory use
without advancing the live operational controller.

## Executed source-bound checks

Baseline runtime blob: `d94cfacd01fc5f29ebac97468e1fb01d786fa450`, read from
main `09f7566fb9f90dfe2a86052b347ca4eaa7e5ada9` and matched to retained bytes.
This includes the prior PR10105 ordered cash-trough correction.

New runtime blob: `5f93719313bbb9f41c298dae803c121d88d041aa`, SHA256
`9776d78e61cbaf2e0696b443ff9cd93858b9d06ae98b990687fe3017c2c010b1`.
New test blob: `37b87f6f00d86db5f226005bf6baeab9fdeda94c`, SHA256
`50137b32b25ca46c105859440f0e5d9ea95e304ac51d35fa208c5bccf684979e`.

Fourteen new methods pass using the pinned actual engine. They exercise nested
mutable state, independent control/candidate copies, exactly one current parent
call, no-option behavior, terminal action reuse, failures, both player positions,
complete cash/productive-state equality, and unchanged engine function objects.
The combined four test modules pass 57 methods, including the existing 240
whole-queue official-interpreter differential cases. Python 3.13.5, cloud Linux.

The exact existing KEEL composition source blob
`9008c09ddc18a0b059ce0360c0ac6564acab2190` is consumed without edits. Its existing
`owner.fork_parent` plugs in directly; the test observes one actual parent call,
one factory invocation, and no changed live Arlene operational state. This is a
factory-contract test with service/labor disabled, not a new complete composition
panel or proof that recursively enabling all optimizers fits the time budget.

Three additional calls use the retained development decision121 input, SHA256
`5a39be040a49e22747b96c1dc916e6071d04e5e58da45d62e2223b8f15c23e61`:
old default, new default, and new explicit factory all return the retained action
and identical decision diagnostics; input observations remain unchanged. The
explicit path creates three continuations. This is an action replay, not a game.

## Reproduction

Use the existing source pack from run34155188751/artifact10030711718 or its saved
copy. ZIP SHA256: `4aa144004e07933c09084be957be7b4baa0bf51a01df4fe606244ea037fcd1f5`.
The loader verifies the three official engine Git blobs before executing them.
No network download or new source-transport job is needed.

```sh
export T10_SOURCEPACK=/absolute/path/to/unpacked-sourcepack
cd revenue/kaggriculture/cloud-labor-capital
python -m unittest -v test_labor_capital test_engine test_cash_trough test_forecast_fork
```

For an isolated copied-file replay, set `T10_COMPOSITION_SOURCE` to the exact
saved KEEL composition.py. In a repository checkout the test uses its existing
sibling path automatically. The separate evidence bundle preserves the complete
executed source, logs, retained input and three-call replay script.

## Boundaries and attribution

No selector objective, economic rule, forecast horizon, market order, or prior
cash-trough behavior was changed. The forecast remains conditional on current
visible shops and zero rival orders. A new fork can supply a bounded alternate
continuation; it does not inject a calibrated rival model or future knowledge.
T10 does not automatically recurse into future hiring/selector optimization.

Original T10/KEEL/T04 credits, source pins and frozen game evidence remain intact.
ADMISSION owns the separate idle_hire implementation and its publication status.
No peer path, canonical selected archive, held bank, game seed, external
submission, paid service, or owner-PC state was changed. No new win-rate,
leaderboard, runtime-bound, revenue, or broad hosted-CI claim is made.
