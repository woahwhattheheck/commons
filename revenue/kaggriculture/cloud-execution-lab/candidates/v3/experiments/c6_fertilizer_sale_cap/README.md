# C6 — accounting-owned fertilizer sale cap

Evaluation-only V3.1 experiment. This directory is outside `overlay/**`, so it is not
included by `build_v3.py` and changes no production default, package, evaluator, or
Kaggle submission artifact.

## Source theorem

The frozen V3.1 R04 tuple enables `sale_fertilizer=True`. That removes `FERTILIZER`
from E184's `SALE_EXCLUDED`, so after `ADVANCE_START=288` E184 may pull an authored
future tape `SELL FERTILIZER` into the current callback and records an equal
`sale_window_debts[due_step][FERTILIZER]` obligation.

E184 protects consumers it can see in the current action, queued native work, and the
future tape (`PICKUP` and `BUY_PRODUCT`). V219's late-tomato fertilizer loaders are
different: their worker roles are created dynamically from observed successful hires.
On day 24 V219 can create two crop workers with five-unit fertilizer loading targets;
on day 27 it can create one dedicated fertilizer worker with a ten-unit target. Those
live role obligations are not represented as future tape rows.

C6 therefore does **not** disable fertilizer sale advancement globally. It snapshots
E184 fertilizer debt before the parent call, measures only positive debt booked by that
same callback, and may cancel only those exact units when already-confirmed V219 roles
still need fertilizer. Cancellation refunds exactly matching newly-booked debt so the
original future tape units become eligible again at authored due steps.

A partial cancellation restores the **latest** newly-booked due units first. Nearer E184
debt remains intact, preventing a nearer native sale from being re-enabled while the
confirmed V219 worker is still approaching/loading at the shed.

## Market-row custody

The official market is positional: both players' raw market arrays execute slot by slot.
Therefore a full C6 cancellation never deletes or compacts the E184-owned row. It replaces
that exact raw slot with the engine's inert empty-row placeholder `[]`. Every later parent
BUY/HIRE/SELL row retains its exact index, executable-prefix membership, content, and rival
pairing. A partial cancellation changes only the owned FERTILIZER quantity in place.

## Ownership and fail-closed rules

The transform requires all of the following:

- exact live baseline tuple: horizon 8, opening 0, row-order ON, evening-flush ON,
  sale-fertilizer ON, cattle-early ON;
- a positive same-callback increment in E184 `FERTILIZER` debt;
- an already-confirmed day-24/day-27 V219 role with `needs_fertilizer=true` and
  `loaded=false`;
- strict non-bool, non-negative integer quantities;
- exactly one current `SELL FERTILIZER` row whose quantity equals the newly-booked
  E184 debt, proving the row is E184-owned under the parent's same-item blocking rule;
- projected post-sale shed fertilizer below the still-unloaded V219 target.

If any ownership, schema, quantity, worker, or ledger condition is ambiguous, the exact
parent action and debt ledger are returned unchanged. Native/tape fertilizer sales,
V233 credit sales, inherited E184 debt, BUY/PICKUP/HIRE rows, worker routes, other
products, and unrelated debt entries are not rewritten or reindexed.

## First gate: structural reachability

`census.py` decodes all 13 frozen 719-step tapes and enumerates authored fertilizer
sales after E184's advance start. It then checks whether any such sale lies within the
8-step E184 horizon after V219 workers can be confirmed on day 24, plus the forced-plan-2
day-27 window. The dedicated workflow **fails** if this overlap count is zero. A source
mechanism with no frozen activation opportunity is a C6 NO-LANE and should be closed,
not sent to an economics panel.

The workflow independently binds the exact frozen-base ancestry plus the R04 and tape
Git blobs at both base and HEAD before running the census, normal/`-O` predecessors, and
syntax checks.

## Evidence boundary

There is deliberately **no competitive-score claim yet**. Passing the source tests and
reachability census proves only that the transform is accounting-owned and structurally
reachable on the frozen policy. Any surviving arm still requires callback-level causal
telemetry (new E184 debt -> withheld fertilizer -> later V219 pickup/FERTILIZE -> realized
production) and paired opponent-diverse `Δown`, `Δrival`, `Δmargin` before integration or
promotion. No default, package, evaluator, or Kaggle mutation is authorized by this PR.
