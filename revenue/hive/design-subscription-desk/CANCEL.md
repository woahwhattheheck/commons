# Fieldwork queue cancellation companion

`queue_cancel.py` is an operator-only companion for the shipped Fieldwork design-subscription desk. It closes an obsolete request without manufacturing a design delivery or approval, preserves the reason in the request history, and advances the one-active-request queue when necessary.

## Compatibility rule

Fieldwork's shipped browser treats `complete` as its only terminal request status. To stay additive and avoid changing LINDEN-1129's landed app, this companion stores a cancelled request in that existing terminal status and adds a final `cancelled` history event beginning with:

> Cancellation is terminal; no delivery acceptance is implied.

The command output also returns `"cancelled": true`. Operators should use the history event—not the terminal storage label—as the business meaning of the closure.

## Safe use

Read the target request's current `id` and `version` from `GET /api/workspaces/<workspace-id>` or the local SQLite-backed operator view, then run:

```bash
python queue_cancel.py <request-id> \
  --db ./data/desk.sqlite3 \
  --expected-version <current-version> \
  --reason "Customer withdrew the request" \
  --confirm-request-id <request-id>
```

The repeated request id is intentional. It prevents a copied or mistyped target from being cancelled accidentally. A stale version fails without mutation.

## Queue behavior

- Cancelling `production`, `review`, or `revision` closes that request and promotes exactly one queued request using Fieldwork's existing ordering: lowest priority number, then creation time, then request id.
- Cancelling a `queued` request closes only that request and does not disturb the active request.
- Already-terminal requests refuse cancellation; inspect history before taking another action.
- All work happens in one `BEGIN IMMEDIATE` transaction. Two operators racing on the same expected version cannot both cancel or advance the queue.
- The tool refuses a missing database instead of silently creating an empty SQLite file.

No email, payment, customer, provider, hosted identity, or external deployment action is performed.

## Focused acceptance

From this directory:

```bash
python -m unittest -v test_queue_cancel.py
python -m py_compile queue_cancel.py test_queue_cancel.py
```

The test schema matches the current Fieldwork tables and its partial unique index for one active request per workspace.
