# C4 — public town-demand boundary timing

Status: **default-off practice arm; no score or promotion claim.**

## What C4 is — and is not

The official market is simultaneous from the agent's perspective. A player does not observe the
rival's current action before returning its own, so C4 does **not** attempt to identify a
"quiet rival step" or predict hidden orders.

There is, however, a deterministic public timing boundary in the official engine:

1. market rows execute;
2. town demand executes afterward;
3. unlocked shops consume their products every 4 steps;
4. town center consumes every non-fertilizer product every 24 steps;
5. prices refresh from the resulting inventory.

Current V3.1 E184 can reserve stock-backed future tape sales up to eight turns early. That may
move an authored sale from *after* a known town-consumption tick to *before* it. C4 tests one
narrow hypothesis: do not let a **new E184 reservation** cross a deterministic public demand
tick for the same item. Leave the authored future sale in place and let the incumbent policy
try again after demand has reduced market inventory.

## Source contract

C4 snapshots the player's existing `sale_window_debts`, then executes the **full unchanged V3.1
parent**, including shipped `ROW_ORDER -> EVENING_FLUSH -> OPEN_ROUNDTRIP` composition. Only after
the final parent action exists does C4 compare the post-parent debt map and consider debt added
by that exact callback.

A new reservation is eligible for rollback only when:

- its due step is in the future;
- the standard public demand clocks are type-strict integers 4 and 24;
- every unlocked shop name is a known official shop;
- at least one public town tick between current step (inclusive) and due step (exclusive)
  deterministically consumes that item;
- the final parent action contains exactly one matching SELL row with enough strict-int quantity
  to reverse the new E184 reservation.

All edits are proven first. Then C4 atomically subtracts only the newly-created cross-tick debt
and the same quantity from that final SELL row. Existing debt, worker commands and unrelated
market rows are untouched. If the parent action has multiple same-item SELL rows (for example a
later wrapper created another row), C4 fails closed rather than guessing which row owns the E184
quantity.

If an E184 row is fully rolled back, C4 replaces that **final raw market slot** with `[]` rather
than deleting/compacting it. Because no incumbent wrapper runs after C4, every unrelated parent
row retains its exact raw index against the rival's lockstep market queue. This post-parent
placement is a deliberate custody constraint.

Any malformed/ambiguous state, unknown shop, nonstandard clock or invalid debt shape preserves
the exact parent action and parent debt map.

## Why this is not automatically a win

Withholding our pre-tick supply can improve the quote seen by our delayed sale, but it can also
improve the rival's current or later quote. The official lockstep market externality therefore
makes paired competitive margin (`Delta own - Delta rival`) mandatory. Own receipts alone are
not a promotion signal.

## Gate

Source custody must pass first. Then run exact-package official-interpreter paired seats against
multiple opponent families with telemetry for:

- reservations proposed vs rolled back, item/step/due step/units;
- public demand tick and unlocked shops responsible;
- pre/post-tick market inventory and quote;
- eventual authored sale fill and realized cash;
- own cash, rival cash and paired margin;
- any stranded/unsold inventory or market-row-cap interaction.

Kill immediately on malformed-state mutation, unrelated parent-row movement, debt mismatch,
increased unsold terminal inventory, or negative paired margin. No default/package/Kaggle
mutation follows from source tests alone.
