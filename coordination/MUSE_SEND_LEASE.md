# Muse / OneWriter atomic send lease

This protocol closes the failure mode where multiple concurrent sessions can observe the same single-writer selection and independently perform the same outbound provider mutation. A bare `SELECTED` decision is **not** provider-send authority.

## Authority boundary

This is a coordination layer only. It can authorize at most one session to *attempt* one provider mutation for an exact outbound generation. It does not authenticate the provider, prove that a message was delivered, prove buyer acceptance, create a contract, prove payment, book cash, or create revenue.

Every returned state therefore keeps provider-send-independent-verification, buyer-acceptance, contract, payment, cash, and revenue authority false. A recorded provider message id is a retained claim until independently checked against the provider.

## Identity

One lease binds:

- `operation_key`
- `counterparty`
- `route`
- `purpose`
- selected seat
- selected `session_nonce`
- issue time and expiry

The semantic collision key is the exact first four fields. Repeating the same semantic generation converges on the existing lease. It never mints a second consumable selection merely because another session asks.

The `session_nonce` must distinguish concurrent chat/session executions even when they share the same Slack user/writer identity.

## State machine

```text
request/election
    |
    v
  LEASED  -- no send authority; HOLD_UNTIL_CONSUME_GO
    |
    | atomic CONSUME by exact selected session before expiry
    v
 CONSUMED -- exactly one GO_ONCE token exists
    |
    | exact COMMIT(session, go_token, provider, provider_message_id)
    v
   SENT   -- terminal coordination record
```

Expiry is deliberately fail-closed:

```text
LEASED   -- expiry --> HOLD_EXPIRED_UNCONSUMED
CONSUMED -- expiry --> HOLD_NEEDS_RECONCILIATION
```

A consumed-but-uncommitted lease is ambiguous because the provider mutation may have happened immediately before a crash. It cannot be silently reissued. An operator must perform an authenticated provider census and record reconciliation:

- provider receipt found -> `SENT`
- no provider send found -> `HOLD_RECONCILED_NO_SEND`

Even the latter does not silently reopen the same semantic generation. A fresh outbound generation requires an explicit new operation key / election decision.

## Atomic consumption

`consume_current()` opens SQLite with `BEGIN IMMEDIATE` and performs a compare-and-swap from `LEASED` to `CONSUMED` against the row version. Only the transaction that performs that transition receives the random `go_token` and `send_gate=GO_ONCE`.

Concurrent later consumers observe `CONSUMED` and receive HOLD. A different session receives `HOLD_SESSION_MISMATCH`. Changed operation key, counterparty, route, or purpose is rejected rather than treated as another view of the same lease.

This is the critical difference from a chat-visible `SELECTED` message: observing state is not consuming authority.

## Commit and crash recovery

The exact selected session must retain its GO token until provider mutation returns. It then calls `commit_current()` with the exact provider and provider message id.

Commit is idempotent only for the same complete tuple. A changed provider id, session, or GO token fails closed. Provider receipt tuples are unique across leases, preventing one retained receipt from being reused to close a second generation.

If the process crashes after GO but before COMMIT, expiry moves the lease to `HOLD_NEEDS_RECONCILIATION`. Never send again first and reconcile second.

## Audit receipts

Every state transition appends a canonical-JSON SHA-256 chained audit event. `status()` replays the chain and rejects digest/predecessor tampering. The audit records coordination causation; it is not an independent provider receipt.

## Current-time boundary

Public mutation entry points are `issue_current`, `consume_current`, `commit_current`, `expire_current`, and `reconcile_current`. Their process clock is captured in a closure at module initialization. Explicit-time helpers are private and exist only for deterministic tests.

## Reference CLI sequence

The CLI is intentionally explicit. Illustrative field values only:

```bash
python coordination/muse_send_lease.py --db /secure/muse.sqlite3 issue \
  --operation-key GEN-20260917-A \
  --counterparty ExampleCo \
  --route sales@example.test \
  --purpose 'paid reconciliation workshare' \
  --seat Z-Sol-1447 \
  --session ZSOL1447-SESSION-NONCE \
  --ttl 300

# SELECTED/LEASED output still means HOLD.
# Immediately before provider mutation:
python coordination/muse_send_lease.py --db /secure/muse.sqlite3 consume \
  --lease-id <lease_id> \
  --operation-key GEN-20260917-A \
  --counterparty ExampleCo \
  --route sales@example.test \
  --purpose 'paid reconciliation workshare' \
  --session ZSOL1447-SESSION-NONCE

# Only decision=GO with send_gate=GO_ONCE authorizes this session to attempt once.

python coordination/muse_send_lease.py --db /secure/muse.sqlite3 commit \
  --lease-id <lease_id> \
  --session ZSOL1447-SESSION-NONCE \
  --go-token <go_token> \
  --provider gmail \
  --provider-message-id <provider_message_id>
```

## Test contract

`test_muse_send_lease.py` covers:

- selection without consume is HOLD;
- two simultaneous consumers receive exactly one GO;
- repeated consume cannot replay GO;
- wrong session and changed route fail closed;
- duplicate semantic requests converge to one lease;
- exact commit idempotency and changed-tuple rejection;
- provider receipt uniqueness across leases;
- consumed expiry requires provider reconciliation;
- no-provider reconciliation remains HOLD and does not silently reissue;
- unconsumed expiry does not silently reissue;
- audit-chain tampering is detected;
- current-time entry points resist ordinary later clock monkey-patching;
- bool/int and invisible Unicode identity aliases fail closed.

Run both ordinary and optimized Python because control-plane validation must not depend on assertions:

```bash
python -m unittest -v test_muse_send_lease.py
python -O -m unittest -v test_muse_send_lease.py
python -m py_compile coordination/muse_send_lease.py test_muse_send_lease.py
```

## Integration rule for Muse

For new outbound elections after adoption:

1. Muse may announce `SELECTED`, but must also issue a lease bound to the exact session nonce.
2. Agents must treat selection/lease observation as HOLD.
3. Immediately pre-provider, the selected session atomically consumes the lease.
4. Only the unique GO holder may perform the one provider mutation.
5. The holder commits the provider receipt immediately after mutation.
6. Any crash/timeout after GO enters reconciliation before any later send is considered.

Until the Muse runtime actually implements this lease/consume handshake, a bare `SELECTED` remains insufficient evidence of atomic single-writer exclusion when multiple sessions share an identity.