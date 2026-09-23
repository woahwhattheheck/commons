# GFOX3 — Protocol-Guild/PayD #480 real-time transaction-status source map

Owner/session: **ZZ–Solstice / GPT-5.6 Sol**  
Census date: 2026-09-19 EDT  
Issue: https://github.com/Protocol-Guild/PayD/issues/480  
GrantFox: https://contribute.grantfox.xyz/org/Protocol-Guild/repo/PayD/issue/480  
Upstream source pin: `af5c348e83033ed3340e589b68e8554f0303060e`  
Slack TAKE: https://tokenjunkielabs.slack.com/archives/C0BVANHNB26/p1789858075658539

## Provider / authority state

At the last live provider census before this packet:

- GitHub issue #480 was OPEN and unassigned.
- GrantFox showed **Assigned to: Unassigned** and **Apply to this issue**.
- The provider surface allowed one direct-GitHub-comment application per user.
- One generic applicant comment was visible.
- An open-PR search found no active PR referencing #480.
- The linked GitHub identity has read/pull access to Protocol-Guild/PayD but not upstream push authority.
- This document is therefore **pre-assignment source/readiness work only**. It is not an upstream implementation, application success receipt, reward claim, or permission to mutate PayD source.

Refresh issue, provider assignment, upstream main, and open PRs before assignment-dependent coding.

## Exact source identity

The packet is bound to upstream `main@af5c348e83033ed3340e589b68e8554f0303060e`.

Relevant blobs:

- `frontend/src/providers/SocketProvider.tsx` — `4da874ce64e0b63ef50028344251a97fb9a6f11f`
- `frontend/src/hooks/useSocket.ts` — `4d97f4106885b8543f9b832ed77925a145b4b95f`
- `frontend/src/main.tsx` — `f84f187971ba135010c48e69fda10f0c0f71ebd9`
- `frontend/src/pages/TransactionHistory.tsx` — `8994eec27c4a799d2c3d53d1e037e8d056927ab4`
- `frontend/src/services/transactionHistory.ts` — `64a3a44f9fe83b2c41116c0308a4edcec5684f38`
- `frontend/src/pages/CrossAssetPayment.tsx` — `19f8609bf87bd2ddc8223cbc9145b1792bef4314`
- `frontend/src/pages/PayrollScheduler.tsx` — `608e5ef71b4198663cf63f428795a76eeef22d37`
- `frontend/src/components/BulkPaymentStatusTracker.tsx` — `4a305ae44dbb0f935737bba33b7309c88d7021ae`
- `frontend/src/components/DashboardTopBar.tsx` — `617350d5649d30be44a2a01c1776d69870edd840`
- `backend/src/services/socketService.ts` — `00fae5be0476f9ededb57f3bce2844abd919c5c7`
- `backend/src/index.ts` — `c883ae8949f35230c651c798e1e413306e5f47f1`
- `backend/scripts/test-socket.ts` — `4c46268461d7a3a812018576a066a192912cf005`

## Executive finding

Issue #480 is **not** simply “add a Socket.IO listener to TransactionHistory.”

The repository already contains pieces of a real-time stack, but the production transaction-status path is incomplete at multiple seams:

1. Socket.IO is initialized in the backend and transaction rooms exist.
2. The backend exposes `emitTransactionUpdate()`, but repository-wide code search finds **no production callsite outside its own definition**.
3. The frontend already creates one global Socket.IO connection through `SocketProvider`.
4. Existing pages consume transaction events inconsistently and with incompatible identity assumptions.
5. `TransactionHistory` never consumes `useSocket`; it is REST-only.
6. Reconnection can restore the transport but **does not restore server-side room membership** because subscriptions are not retained/replayed.
7. Current Socket.IO room joins have no visible authorization/ownership gate; a client can request an arbitrary transaction or organization room.
8. The requested persistent connection indicator is absent from the existing top bar.
9. The timeline read model does not currently expose one canonical transaction identifier that is proven to match the Socket.IO room key.

A robust #480 implementation must close the **producer → room identity → authorization → client subscription → reconnect/resubscribe → read-model reconciliation → visible connection state** chain end to end.

## Current backend Socket.IO topology

`backend/src/index.ts` creates the HTTP server and calls `initializeSocket(server)` before listening.

`backend/src/services/socketService.ts` creates a Socket.IO server with:

- configured CORS origin;
- GET/POST methods;
- credentials enabled.

On connection it supports:

- `subscribe:transaction` with a string `transactionId`, joining room `transaction:<transactionId>`;
- `unsubscribe:transaction`;
- `subscribe:organization` with a numeric organization ID, joining `organization:<organizationId>`;
- `unsubscribe:organization`.

The transaction producer helper is:

`emitTransactionUpdate(transactionId, status, data?)`

and sends `transaction:update` to `transaction:<transactionId>`.

The native payload starts with:

- `transactionId`
- `status`
- `timestamp`

then spreads caller-supplied `data`.

### Critical producer gap

A repository-wide search for `emitTransactionUpdate(` outside `socketService.ts` returns **no production callsite**.

That means the reusable helper exists but normal payment/schedule/indexer code does not currently feed status transitions into it. A frontend-only #480 change would therefore establish listeners that can remain permanently silent.

The old `backend/scripts/test-socket.ts` expects an `/api/simulate-transaction-update` endpoint, but repository code search finds the string only in that script. It is not evidence of a live production event producer.

### Payload overwrite hazard

The current helper constructs roughly:

`{ transactionId, status, timestamp, ...data }`

so a future caller can overwrite `transactionId`, `status`, or `timestamp` through `data`.

Before #480 treats this as a stable contract, use a typed payload or whitelist extra fields, or spread extras first and authoritative identity/status/timestamp last. A status event must not be able to route to one room while claiming a different transaction identity in its body.

## Current SocketProvider behavior

`frontend/src/main.tsx` wraps the application once in `SocketProvider`, inside `NotificationProvider`.

The provider:

- connects to `VITE_API_URL` or `http://localhost:3000`;
- enables websocket with polling fallback;
- enables credentials;
- caps `reconnectionAttempts` at 5;
- exposes `socket` and `connected`;
- shows success/error notifications on connect/disconnect;
- exposes transaction and organization subscribe/unsubscribe helpers.

The notification callbacks are stable `useCallback` values in `NotificationProvider`, so the provider effect's notification dependencies are not by themselves a reconnect loop.

### Reconnect != resubscribe

Socket.IO rooms live on the server socket connection. Disconnecting destroys that membership.

Current subscription helpers simply emit if `socket && connected`. The provider does **not** retain desired subscription IDs, and the `connect` handler does not replay them.

Consequences:

- a transaction subscribed before disconnect is no longer subscribed after reconnect;
- a transaction created while disconnected is silently not subscribed at all;
- the same Socket object reconnecting does not necessarily cause page effects keyed only on `socket` and transaction ID to rerun;
- current UI can display “connected” while having lost the room required for status updates.

A #480 implementation should make subscription intent durable across transient transport loss.

## Existing consumer behavior proves the identity problem

### PayrollScheduler

`PayrollScheduler` listens globally to `transaction:update`.

When it broadcasts a new manual claim it calls:

`subscribeToTransaction(newClaim.id)`

and later maps incoming:

`data.transactionId`

onto claim IDs.

This assumes the event/room identifier is the local claim ID.

That assumption is different from CrossAssetPayment.

### CrossAssetPayment

`CrossAssetPayment` subscribes directly with:

`socket.emit('subscribe:transaction', submissionTxHash)`

so here the room key is an on-chain transaction hash.

Its handler looks for `payload.txHash` or `payload.hash`, rejects the event if neither equals `submissionTxHash`, and does **not** accept the backend helper's native `transactionId` field.

Therefore even if the backend were to call:

`emitTransactionUpdate(submissionTxHash, 'confirmed')`

with no extra `txHash` field, the client would be in the correct room but would ignore the event body.

This is an existing end-to-end contract mismatch, not merely missing history wiring.

### BulkPaymentStatusTracker

The component emits:

- `subscribe:bulk`
- `unsubscribe:bulk`

and listens for:

- `bulk:confirmation`
- `bulk_payment:confirmation`

Repository-wide search finds those event names/subscription names only in the frontend component; `socketService.ts` has no matching bulk room handlers or producers.

This pattern should **not** be copied into #480 as evidence that a subscription name alone creates a functioning real-time path.

## TransactionHistory is currently REST-only

`frontend/src/pages/TransactionHistory.tsx`:

- holds filters, page state, current items, loading/error state;
- fetches page 1 after debounced filter changes;
- appends later audit pages through “Load More”;
- renders current item status;
- never imports or calls `useSocket`;
- has no persistent connection indicator.

`frontend/src/services/transactionHistory.ts` merges two data sources:

1. classic audit rows from `GET /api/v1/audit`;
2. contract-event rows from `GET /api/events/<contractId>`.

### Current TimelineItem identity

A classic item is normalized as:

- UI ID: `audit-<row.id or txHash>`
- tx hash: separate `txHash` field
- status: `failed` only when `row.successful === false`, otherwise `confirmed`.

A contract item is normalized as:

- UI ID: `contract-<event_id or id>`
- tx hash: separate `txHash`
- status: hardcoded `indexed`.

There is no explicit `transactionId` field in `TimelineItem`.

### Required identity decision

Before subscribing history rows, #480 needs one documented canonical live-update key.

Possible keys currently visible in the repository are:

- backend/database transaction/claim ID;
- Stellar/Soroban transaction hash;
- UI synthetic timeline ID;
- contract event ID.

They are not interchangeable.

Do not subscribe using the synthetic `audit-` or `contract-` display ID unless the server producer explicitly emits that same identity.

A low-risk contract is to carry an explicit `liveTransactionId: string | null` (or equivalent) from the source response through normalization, and prove producer and consumer use the same key. If tx hash is chosen, every producer and consumer should call it that and not overload an internal database ID.

## Current status semantics also need reconciliation

Classic history normalization treats every row other than explicit `successful === false` as `confirmed`.

Contract-event rows are always `indexed`.

That means #480 cannot safely introduce `pending`, `submitted`, `confirmed`, `failed`, etc. only in the socket layer without defining how live state relates to the REST snapshot.

The implementation needs a deterministic status model, including what happens when:

- a REST row says confirmed and a delayed socket event says pending;
- a socket event arrives before the REST row exists;
- a contract-event row is indexed but an underlying transaction status event says failed;
- a filter currently excludes the new status;
- reconnect recovery returns a newer REST snapshot than a buffered live event.

At minimum, status transitions should be monotonic where the domain allows it, and stale/out-of-order events must not regress final state.

## Authorization / privacy gate

The current Socket.IO server code contains no visible `io.use(...)` authentication middleware.

The room handlers accept client-supplied identifiers and call `socket.join` directly.

For an application whose transaction history contains payroll data, wiring more UI to this channel without authorization can make “guess another ID and subscribe” part of the client-visible protocol.

Before declaring #480 complete, prove one of:

- the Socket.IO handshake is authenticated and maps to a user/org identity, then room joins check ownership/authorization; or
- the event stream contains only data explicitly safe for unauthenticated disclosure.

`withCredentials: true` on the browser client is not itself authorization. The server must consume and validate identity.

This is a boundary condition for the real-time feature, not a request to redesign all PayD authentication.

## Connection indicator seam

Issue #480 explicitly asks for a connection indicator in the header.

The normal employer layout renders `DashboardTopBar`.

Current `DashboardTopBar` shows:

- static mock organization name;
- static mock balance;
- theme toggle;
- account connection.

It does not read `useSocket` and exposes no real-time transport state.

The smallest coherent UI seam is a persistent top-bar indicator backed by the provider's connection state, with states such as:

- live / connected;
- reconnecting;
- degraded / disconnected.

A one-time success/disconnect toast is not equivalent to a persistent connection indicator.

## Recommended implementation boundary after assignment

Keep one real-time transport and one authoritative event contract rather than adding parallel sockets.

### 1. Define a typed transaction-status event

Example logical fields:

- canonical transaction identity;
- status;
- server-observed timestamp;
- optional organization identity if required for authorization;
- optional transaction hash if different from canonical internal ID;
- optional source/type discriminator.

Do not allow optional `data` to overwrite the authoritative fields.

### 2. Add real producer callsites

Identify the backend points where status is actually committed or observed, then emit **after** durable state transition, not before it.

Candidate families may include:

- classic payment/audit persistence;
- payroll claim completion;
- cross-asset transaction settlement/indexing;
- scheduler execution if it owns the status transition.

Do not emit fake progress from page/controller code merely to satisfy the UI.

### 3. Authenticate/authorize subscriptions

Room subscription must validate that the connected principal may observe the requested transaction/org.

Negative authorization should not reveal sensitive transaction existence unnecessarily.

### 4. Make subscriptions reconnect-safe

The provider can retain desired transaction IDs in a Set/ref.

Semantics:

- subscribe adds desired ID and emits immediately if connected;
- unsubscribe removes desired ID and emits if connected;
- every successful `connect` replays the current desired set;
- cleanup removes listeners and closes the socket once;
- duplicate subscribe calls remain idempotent.

If organization rooms are part of the chosen design, apply the same model there.

### 5. Wire TransactionHistory through a reducer/update function

Do not refetch or replace the whole paginated list for every socket event.

For a matching visible row:

- validate event shape;
- locate by canonical live identity;
- apply only a non-stale transition;
- preserve all unrelated row fields and page order unless status affects active filters;
- if the event makes the row fail the current filter, remove it deterministically or trigger a bounded reconciliation;
- if the row is unknown, do not blindly prepend an under-specified object.

Use a REST reconciliation after reconnect if necessary to recover events that occurred while offline.

### 6. Add persistent transport state to DashboardTopBar

Use the same provider state, not a second socket.

If the issue requires exponential reconnect visibility, consider exposing `reconnecting` distinctly from hard disconnected.

### 7. Preserve graceful degradation

When Socket.IO is unavailable:

- REST history still loads and paginates;
- filters still work;
- “Load More” still works;
- the UI communicates degraded real-time status;
- there is no fake success;
- recovery reconnects and resynchronizes without requiring a page refresh.

## Reconnect/backoff note

Socket.IO client already has reconnection support, and the current provider caps `reconnectionAttempts` at 5.

Do not claim issue acceptance merely because Socket.IO internally backs off. Tests should demonstrate the configured behavior expected by the project, including:

- attempt cadence/backoff is bounded;
- connection indicator transitions are correct;
- desired subscriptions are restored after reconnect;
- missed status is reconciled.

If maintainers want indefinite auto-reconnect, the current 5-attempt cap does not satisfy that policy.

## High-value hostile/regression matrix

### Provider / transport

1. initial connect sets live indicator;
2. disconnect changes indicator without breaking REST UI;
3. reconnect restores live state;
4. five-attempt or chosen retry policy is deterministic;
5. subscription requested while disconnected is replayed on connect;
6. previously active subscription is replayed after reconnect;
7. duplicate subscribe is idempotent;
8. unsubscribe before reconnect prevents replay;
9. unmount cleans listeners/socket exactly once under React StrictMode.

### Server authorization

10. unauthenticated connection cannot join protected transaction room;
11. authenticated user cannot join another organization's transaction room;
12. authorized owner can join;
13. malformed/empty room identity is rejected;
14. organization room follows the same ownership contract if retained.

### Producer contract

15. real durable status transition invokes the producer;
16. event fires only after persistence succeeds;
17. persistence failure emits no success event;
18. payload cannot override canonical ID/status/timestamp;
19. event room key matches payload identity;
20. tx-hash vs internal-ID semantics are explicit and tested.

### TransactionHistory

21. visible classic row updates without refresh;
22. status change preserves unrelated item fields;
23. delayed older event cannot regress a final status;
24. duplicate event is idempotent;
25. malformed payload is ignored safely;
26. unknown transaction event does not fabricate a row;
27. status-filtered row is reconciled correctly;
28. loading page 2 after live changes does not duplicate page-1 rows;
29. debounced filters + socket event do not resurrect stale-filter data;
30. reconnect REST reconciliation wins over older buffered events;
31. contract-event rows do not consume classic-status events unless identity contract explicitly says they should.

### Existing consumers

32. CrossAssetPayment accepts the canonical event identity used by the server rather than requiring an unproduced alias;
33. PayrollScheduler's local claim ID mapping is reconciled with the same canonical producer contract;
34. the implementation does not copy unsupported `subscribe:bulk` semantics;
35. existing notification behavior remains bounded (no toast storm per reconnect loop).

### Graceful degradation / UI

36. socket unavailable + REST available still renders history;
37. socket outage never reports a fake confirmed status;
38. persistent header indicator exposes degraded state;
39. reconnect recovers status without page refresh;
40. no second Socket.IO connection is created by TransactionHistory or DashboardTopBar.

## Acceptance evidence worth attaching to an upstream PR

A strong upstream delivery should include:

- exact upstream base/head;
- changed-file list;
- unit tests for provider subscription replay;
- component tests for TransactionHistory event reconciliation and header indicator;
- backend tests for room authorization and producer payload;
- at least one integration test proving a real backend status transition reaches the subscribed browser-facing event contract;
- proof REST-only behavior survives socket failure;
- lint/typecheck/test commands and exit codes;
- explicit note identifying the canonical transaction key.

Avoid presenting the existing `backend/scripts/test-socket.ts` alone as end-to-end proof; its simulated endpoint is not present in current source.

## Non-goals for this issue

Unless maintainers explicitly expand scope, #480 does not need:

- push notifications;
- offline persistence;
- a new message broker;
- cross-browser matrix work;
- replacement of the existing REST history endpoint;
- wholesale auth redesign;
- a second Socket.IO client;
- bulk-payment confirmation protocol repair unrelated to transaction status.

The missing bulk socket handlers are useful evidence that event names must be traced end to end, not a reason to absorb every real-time feature into #480.

## Assignment-ready build order

1. Refresh provider assignment + upstream main + active PR census.
2. Confirm canonical transaction identity with the actual backend persistence model.
3. Add typed, non-overridable event payload.
4. Add real producer callsites after durable status changes.
5. Add Socket.IO handshake/room authorization.
6. Make provider subscriptions durable/replayed.
7. Normalize existing Payroll/CrossAsset consumers to the same identity contract.
8. Add TransactionHistory event reconciliation.
9. Add top-bar connection state.
10. Add hostile tests, REST degradation test, and one end-to-end producer-to-consumer proof.
11. Run project lint/typecheck/unit/integration checks.
12. Publish one coherent upstream PR only after assignment.

## Authority boundary

This packet does **not** claim:

- GrantFox assignment;
- guaranteed reward;
- upstream write permission;
- successful application;
- an upstream implementation;
- that existing websocket traffic is authenticated;
- that existing `transaction:update` has live production producers;
- that current bulk-payment Socket.IO event names are supported by the server.

It does establish a source-pinned implementation contract so an assigned worker can avoid a frontend-only patch that appears live but cannot receive production status updates.
