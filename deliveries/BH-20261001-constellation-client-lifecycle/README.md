# BH-20261001 · CONSTELLATION-CLIENT-LIFECYCLE

Robust request lifetime and concurrency for the microG GmsCore Constellation (RCS phone-number
verification) service. Private delivery as files only — no competing PR, claim, or publication.

## Provenance (verified, not assumed)

| What | Value |
|---|---|
| Upstream fork | `nwinkelman2/GmsCore`, branch `integration/rcs-current-upstream` |
| Fork HEAD | `0266edd1694cbeac340b59d9287a50112465e0a4` |
| Related upstream PR | `microg/GmsCore` #3360 ("Update constellation base for asterism", head `2a680646cbfaf3a4a484bd4dc8f53c21404c8c4b`) |
| `VerifyPhoneNumber.kt` blob | `9154d33134f3b0534e049bccb7a1c73060b9168e` — **identical** in the fork HEAD and in PR 3360 head; **left unchanged by this work** |
| Module | `play-services-constellation/core` (Gradle path `:play-services-constellation-core`) |
| Toolchain | AGP 8.13.2, Gradle 8.13, Kotlin 1.9.22, JDK 21, compileSdk 35, build-tools 35.0.0, coroutines 1.7.3, Wire 6.2.0, OkHttp 4.12.0 |

The `git hash-object` of `VerifyPhoneNumber.kt` after all edits is still
`9154d33134f3b0534e049bccb7a1c73060b9168e` — see `evidence/provenance.txt`.

## Problem

Every Constellation API request was launched fire-and-forget on a single shared service scope:

```kotlin
serviceScope.launch { handleVerifyPhoneNumberV1(context, ConstellationCallbacksWrapper(cb), bundle, packageName) }
```

That left four concrete lifecycle/concurrency defects:

1. **No caller Binder-death handling.** If the client process died mid-verification, the coroutine
   kept running — waiting on MT SMS (up to 30 min), holding an in-flight gRPC call — delivering a
   result to a dead client.
2. **No per-request cancellation.** Launches were untracked `Job`s; nothing could cancel an
   individual request.
3. **Weak callback exception containment.** `ConstellationCallbacksWrapper` caught only
   `RemoteException`; any other `RuntimeException` from a dead/misbehaving caller proxy escaped the
   launched coroutine and could crash the GmsCore process.
4. **MT-SMS inbox cleanup that erased newer requests.** `MtSmsInboxRegistry` was a **process-global
   singleton**. A second concurrent `verifyPhoneNumber` call's `prepare()` tore down the first
   request's inboxes, and the first request's `finally { dispose() }` then tore down the *second*
   (newer) request's inboxes — unregistering its SMS receivers so its verification silently timed
   out.

## What changed (4 files edited, 1 added; 3 test files added)

### `MtSmsVerifier.kt` — per-request MT-SMS inbox isolation
`MtSmsInboxRegistry` is now a thin **coroutine-context-scoped** facade over a new
`MtSmsInboxScope` element that owns the inboxes of a single request. `prepare`/`get`/`dispose`
resolve to the calling request's own scope, so a request's cleanup can only dispose **its own**
inboxes — it can never erase a newer request's. `MtSmsInbox` now implements a small
`MtSmsInboxHandle` interface so the ownership logic is unit-testable without a real
`BroadcastReceiver`. The registry's public call sites are unchanged, so **`VerifyPhoneNumber.kt`
is untouched** (the calls were already in suspend context).

### `ConstellationRequestDispatcher.kt` (new) — request lifetime
Each request is launched as a cancellable child of the service scope with its own
`MtSmsInboxScope`. The caller's callback binder gets a `DeathRecipient` that cancels **that**
request's `Job` on caller death; exceptions are contained (logged, not propagated to the service
scope); the recipient is unlinked in a `finally`. Cancellation reaches OkHttp purely through
structured concurrency (see the Wire proof) — there is **no** late
`Job.invokeOnCompletion { call.cancel() }`.

### `ConstellationApiService.kt` — wiring
`ConstellationApiServiceImpl` routes all five AIDL entry points through the dispatcher. SDK guards
and null checks are preserved verbatim; `onDestroy` still cancels the whole service scope (which now
cancels every in-flight request as a child).

### `ConstellationCallbacksWrapper.kt` — callback containment
`runRemote` now contains `RuntimeException` as well as `RemoteException`, while **rethrowing**
`CancellationException` so cooperative cancellation is never swallowed.

### `build.gradle` — test deps
Adds `kotlinx-coroutines-test` and `mockito-core` as `testImplementation` only.

## Guarantees mapped to the task

| Task requirement | Delivered by |
|---|---|
| Caller Binder death | `ConstellationRequestDispatcher` links a `DeathRecipient` that cancels the request Job |
| Child-request cancellation | Each request is a cancellable child `Job` of the service `SupervisorJob` scope |
| Callback exception containment | Broadened `runRemote` + Throwable containment in the dispatcher coroutine |
| Status recording | `ConstellationStateStore.recordPhoneNumberVerification` (in the untouched flow) still runs for completed requests; cancelled requests record nothing (no false status) |
| Per-request MT-SMS cleanup that cannot erase a newer request | `MtSmsInboxScope` per-request ownership |
| Preserve disabled-consent / legacy / read modes | `VerifyPhoneNumber.kt` unchanged (blob preserved) |
| Wire cancellation propagates to OkHttp; no late `invokeOnCompletion` | Proven from Wire 6.2.0 source; dispatcher relies on structured cancellation only |
| Do not change auth/entitlements/attestation; no invented hardware/SMS | `AuthManager`, TS.43/entitlement, DroidGuard, and all SMS/challenge logic untouched |

## Wire 6.2.0 cancellation proof

See `evidence/wire-6.2.0-cancellation-proof.md`. Summary: `RealGrpcCall.execute` (jvmMain, tag
`6.2.0`, commit `49cbae3`) suspends in `suspendCancellableCoroutine` and registers
`continuation.invokeOnCancellation { cancel() }` — which calls `okhttp3.Call.cancel()` — **before**
`call.enqueue(...)`, with `initCall` additionally re-checking `if (canceled) result.cancel()`.
Cancelling the request coroutine therefore aborts the HTTP call synchronously, inside Wire.

## Discriminating tests (`src/test`, JVM unit tests)

- `verification/MtSmsInboxScopeTest.kt` — isolation and the headline invariant
  `dispose_cannotEraseANewerRequest`.
- `ConstellationRequestDispatcherTest.kt` — caller-death cancels the request + unlinks;
  already-dead caller cancels immediately; a request failure is contained and does not tear down the
  service scope.
- `ConstellationCallbacksWrapperTest.kt` — `RemoteException` and `RuntimeException` are contained;
  `CancellationException` is not swallowed; successful delivery passes through.

Each test targets one defect above; `evidence/fail-before.log` shows them failing when the defects
are reintroduced (see `evidence/reintroduce-bugs.patch`), and `evidence/pass-after.log` shows them
green against the fix.

## Receipts

- `evidence/pass-after.log` — `:play-services-constellation-core:testDebugUnitTest` with the fix.
- `evidence/fail-before.log` — same task with the defects reintroduced.
- `evidence/reintroduce-bugs.patch` — the minimal diff used to reintroduce the defects.
- `evidence/test-results/` — JUnit XML for the pass-after run.
- `evidence/provenance.txt`, `evidence/tree.txt`, `evidence/toolchain.txt` — environment/provenance.
- `evidence/constellation-lifecycle.patch` — the full change vs fork HEAD `0266edd`.
- `whole-files/` — every edited/added file in full.

See `evidence/RECEIPTS.md` for the exact pass/fail counts and how to reproduce.

## Scope / non-goals

No change to authentication, entitlements, attestation, DroidGuard, or the TS.43 carrier path; no
invented SMS or hardware results; no modification to `VerifyPhoneNumber.kt`; no upstream PR, issue,
or publication. Instrumented (`androidTest`) device tests are out of scope for this container; the
lifecycle/concurrency invariants are covered by host JVM unit tests.
