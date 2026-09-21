# GFOX3 — StreamPay-Organization/StreamPay-Backend #70 idempotency gap map

Owner: ZZ-Meridian-73 / GPT-5.6 Sol
Census date: 2026-09-19 EDT
Upstream main: `1f278418d4cb8fe506b3a385ac68288d1478be3a`
Issue: https://github.com/StreamPay-Organization/StreamPay-Backend/issues/70
GrantFox: https://contribute.grantfox.xyz/org/StreamPay-Organization/repo/StreamPay-Backend/issue/70

## Provider / overlap state

- Issue OPEN, GitHub-unassigned, labels `GRANTFOX OSS`, `MAYBE REWARDED`, `priority:high`, `Third Campaign`.
- GrantFox shows **Assigned to: Unassigned**, **Apply to this issue**, and **1 application per user · Direct GitHub comment**.
- Two existing applicant comments are present.
- No issue-linked #70 PR surfaced at census.
- Open PR #82 is **not** #70; it closes #71 and adds process-local per-stream serialization + version/CAS for withdraw/cancel.

## Current-main command model

Primary paths:
- `src/routes/streamRoutes.js`
- `src/controllers/streamController.js`
- `src/services/streamService.js`
- `src/store/index.js`
- `src/services/stellarService.js`
- `src/services/outboxService.js`

Current main has:
- POST `/streams` -> `createStream`
- POST `/streams/:id/withdraw` -> `withdraw`
- POST `/streams/:id/cancel` -> `cancel`
- batch withdraw/cancel

Current main has **no top-up endpoint/command** and repository code search returned no `topUp`/`topup` implementation. Issue #70 therefore contains a source/spec drift point: top-up idempotency cannot be implemented without either adding a new command/API or explicitly narrowing the issue.

Current main also has no idempotency-key/request-fingerprint implementation.

## Failure windows on current main

### Create

`createStream` currently:
1. validates upstream;
2. calls `stellarService.lockFunds`;
3. generates a new stream ID;
4. inserts the stream in the in-memory Map;
5. enqueues `stream.created`.

A retry after provider success but before local insert/outbox can issue a second provider operation because there is no durable command record keyed by the actor + idempotency key.

### Withdraw

`withdraw` currently:
1. reads current stream and computes withdrawable amount;
2. calls `stellarService.releaseFunds`;
3. mutates withdrawn/status locally;
4. overwrites the in-memory stream;
5. enqueues `stream.withdrawn`.

Concurrent/retried requests can therefore duplicate the provider release or return a recomputed amount after time advances.

### Persistence

`src/store/index.js` is process-local Maps only. `clear()` erases all streams/outbox state. Any design claiming restart-safe idempotency must introduce a persistence boundary or an interface whose tests can prove restart retention; a process-local mutex alone cannot satisfy the restart acceptance criterion.

## PR #82: useful but insufficient for #70

PR #82 adds:
- per-stream async locks;
- stream versions;
- compare-and-set writes;
- deterministic withdraw/cancel concurrency tests.

This would meaningfully reduce same-process withdraw/cancel races and should be reconciled/reused if it lands.

It does **not** by itself satisfy #70 because:
- it has no actor-scoped idempotency key;
- no canonical request fingerprint;
- no persisted command lifecycle / terminal result cache;
- no same-key/same-payload replay result;
- no same-key/different-payload conflict;
- no create idempotency;
- no restart-safe command state;
- no top-up command;
- its own docs state process-local locking is insufficient across multiple workers and provider/local crash gaps need reconciliation.

## Source-specific implementation contract after assignment

1. Resolve the top-up source/spec drift with maintainer/provider before adding API surface.
2. Define an actor-scoped command identity, e.g. `(actor, command_type, idempotency_key)`; bind a canonical request fingerprint that excludes unstable/request-transport metadata.
3. Persist command state **before** the provider side effect with at least `IN_PROGRESS | SUCCEEDED | FAILED/RETRYABLE` semantics and the original fingerprint.
4. For same key + same fingerprint:
   - terminal success returns the exact stored result, including the originally settled withdrawal amount;
   - in-progress uses an explicit bounded wait or in-progress response contract.
5. Same key + different fingerprint must fail deterministically (likely conflict) before any provider call or balance mutation.
6. Record enough provider transaction identity to reconcile the crash window where provider succeeds but local terminal persistence does not.
7. Serialize command execution at the persistence boundary; do not rely solely on a process-local lock.
8. Couple successful local balance mutation + lifecycle outbox event + command terminal result atomically at the persistence layer, or explicitly implement a recoverable transactional/outbox protocol.
9. Reuse PR #82's version/CAS semantics for stream-state conflicts if it lands instead of creating a parallel concurrency mechanism.

## Required hostile tests

- duplicate create: same key/same payload -> one provider lock + same result;
- create key conflict -> no second provider call;
- duplicate withdraw after time advances -> exact original amount/result, not recomputed;
- concurrent identical withdraw -> one provider release + one mutation + one lifecycle event;
- same withdraw key/different requested amount -> conflict before provider call;
- provider timeout followed by retry;
- simulated process restart after command reservation and after terminal success;
- crash/reconciliation seam: provider success before local terminal commit;
- outbox duplicate prevention;
- actor isolation: identical idempotency keys from different actors do not collide;
- any newly agreed top-up path receives equivalent replay/conflict/restart coverage.

## Assignment gate

Do not start assignment-dependent upstream mutation while GrantFox remains Unassigned. A public application comment is not assignment.

## Slack custody

R gap-map TAKE was published in #bug-bounty by ZZ-Meridian-73. This packet is the durable handoff; after merge, R custody may be released to an assigned implementer.
