# EXEC-PACE-2 current-runtime closure (default OFF)

This packet advances the existing `candidates/v4/repairs/gameplay/exec-pace-2`
line only. It does **not** create another V4, execute the legacy `apply_v4`
materializer, modify production files directly, or enable EXEC-PACE-2.

## Boundary closed

The landed detector established the seven-good, 25-contiguous-sample,
`0.03` endpoint-slope observation contract but deliberately left current-runtime
wiring, lifecycle ownership, key-OFF identity and economics open. This packet
provides the missing current-ABI *experiment recipe* without claiming economic
promotion:

* `current_runtime_exec_pace.py` moves observation state from module globals to
  one `PriceTrendState` per current `FrozenSelected` consumer instance.
* `cumulative_advance()` recognizes a real temporal advance anywhere in the
  candidate sale schedule, not merely extra units at the current step.
* `gate_plan()` may veto an advance only when that exact product has a complete
  rising-price window. Delays, unchanged schedules, unsupported products,
  malformed/non-comparable plans, and non-rising products preserve the current
  scheduler decision.
* Forced-feasibility plans are never vetoed by the composition recipe.
* `compose_current_runtime.py` is source-bound: it requires unique exact anchors
  in today's `Features`, frozen-consumer construction, observation boundary, and
  plan-selection boundary. Drift or double-application fails closed.
* The composed feature is `exec_pace: bool = False`; the composed config also
  adds `"exec_pace": false`. No default flip is contained here.

The current ABI seam is intentionally inside `FrozenSelected` before
`seller_choice_rank()` and only after the existing optimizer has produced its
candidate/reference pair. The gate therefore does not create market orders,
change quantities, bypass feasibility, or run a second producer/controller.

## Validation performed here

Development copy, Python normal and `-O`:

* 13 focused tests discovered; 12 PASS + 1 repository-binding test SKIP because
  the standalone `/mnt/data` copy does not contain the production tree.
* The same 12 semantic/composer checks pass under `python -O`.
* `py_compile` passes for runtime module, composer and tests.
* Coverage includes 25-step warmup, slope decision, identical duplicate
  idempotence, step-gap/player reset, per-good missing quote invalidation,
  immediate and mid-window cumulative advance, delay/non-advance, rising-only
  veto, quantity-mismatch fail-open, default-OFF composition, source-drift and
  double-apply rejection.

Once this packet lives inside Commons, the 13th test is mandatory: it locates
`cloud-execution-lab/titan_runtime.py`, `frozen_selected.py` and
`TITAN-CONFIG.json` from the package path and composes/compiles those exact
current sources. It skips only in an out-of-tree standalone copy.

## Still deliberately open

This packet is a current-source experiment component, **not** evidence that the
feature should be enabled. Before any ON/default recommendation, the owner must
execute the materialized current runtime with both seats and opponent-diverse
panels, verify exact feature-OFF returned actions/checkpoint/receipt behavior,
exercise deadline/retry/reconstruction paths, and measure terminal margin with
activation telemetry. Historical `+$377/+369` receipts remain provenance only;
they are not transferred to this ABI.

Canonical integration rule remains unchanged: one `main:candidates/v4`, current
main source wins, and any later conflicting exact owner/source must be consumed
rather than forked.
