# Proof: Wire 6.2.0 suspending `GrpcCall.execute` propagates coroutine cancellation to OkHttp

**Claim under test:** cancelling the coroutine that is suspended in a Wire *suspending* unary gRPC
call aborts the in-flight OkHttp call, with no extra wiring on our side — so the Constellation
request lifecycle can rely on structured cancellation alone and must **not** add a late
`Job.invokeOnCompletion { grpcCall.cancel() }` hook.

**Verified against actual library source**, not documentation or memory:

- Repository: `square/wire`
- Tag: `6.2.0` (commit `49cbae32085ec586b72a447945cafe1b09a08cfd`)
- This project pins exactly this version: `ext.wireVersion = '6.2.0'` in the root `build.gradle`,
  and `play-services-constellation/core/build.gradle` depends on
  `com.squareup.wire:wire-grpc-client:$wireVersion`.
- Call style: `play-services-constellation/core/build.gradle` configures
  `wire { kotlin { rpcRole = 'client'; rpcCallStyle = 'suspending' } }`, so the generated
  `PhoneDeviceVerificationClient` / `PhoneNumberClient` expose `GrpcCall<S, R>` whose `execute` is
  the suspending function used throughout `VerifyPhoneNumber.kt` and `ChallengeProcessor.kt`
  (`...Sync().execute(req)`, `...Proceed().execute(req)`, `...GetConsent().execute(req)`,
  `...SetConsent().execute(req)`).

## The source

`wire-grpc-client/src/jvmMain/kotlin/com/squareup/wire/internal/RealGrpcCall.kt` is the JVM/Android
implementation of `GrpcCall`. The relevant parts, verbatim:

```kotlin
// lines 44-49
override fun cancel() {
  canceled = true
  call?.cancel()                 // okhttp3.Call.cancel()
}

override fun isCanceled(): Boolean = canceled || call?.isCanceled() == true

// lines 51-75
override suspend fun execute(request: S): R {
  val call = initCall(request)

  return suspendCancellableCoroutine { continuation ->
    continuation.invokeOnCancellation {
      cancel()                   // <-- fires on coroutine cancellation, calls okhttp3.Call.cancel()
    }

    call.enqueue(object : okhttp3.Callback {
      override fun onFailure(call: okhttp3.Call, e: IOException) {
        continuation.resumeWithException(e)
      }
      override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
        try {
          responseMetadata = response.headers.toMap()
          val message = response.readExactlyOneAndClose()
          continuation.resume(message)
        } catch (e: IOException) {
          continuation.resumeWithException(e)
        }
      }
    })
  }
}

// lines 136-153 (excerpt)
private fun initCall(request: S): okhttp3.Call {
  check(this.call == null) { "already executed" }
  ...
  val result = grpcClient.newCall(method, requestMetadata, requestBody, timeout)
  this.call = result
  if (canceled) result.cancel()  // <-- covers cancellation that lands before enqueue
  ...
  return result
}
```

## Why this proves the claim

1. `execute` suspends inside `suspendCancellableCoroutine`. Kotlin's
   `CancellableContinuation.invokeOnCancellation { ... }` is invoked **synchronously** when the
   surrounding coroutine (our per-request `Job`) is cancelled.
2. The registered handler calls `cancel()`, which calls `okhttp3.Call.cancel()` on the enqueued
   call. OkHttp then fails the call and stops the network I/O. The continuation is already in the
   cancelled state, so the subsequent `onFailure`/`onResponse` resume is ignored — no result is
   delivered to a cancelled request.
3. The handler is registered **before** `call.enqueue(...)`, and `initCall` additionally re-checks
   `if (canceled) result.cancel()`. So the race window between "coroutine cancelled" and "call
   created/enqueued" is closed in both directions: cancel-before-create and cancel-after-enqueue
   both end in `okhttp3.Call.cancel()`.

This is entirely internal to Wire. Our code gets correct network-abort behaviour simply by
cancelling the request coroutine.

## Consequence for this change (and why no late `invokeOnCompletion`)

The Constellation request dispatcher cancels a request by cancelling that request's `Job` (on caller
Binder death, or on service teardown via the service scope). Because the suspending `execute`
already tears down the OkHttp call through `invokeOnCancellation`, there is nothing left for us to
do at the network layer.

Adding a late hook such as:

```kotlin
val call = client.Sync()
job.invokeOnCompletion { call.cancel() }   // <-- deliberately NOT done
val resp = call.execute(req)
```

would be redundant and strictly worse: `invokeOnCompletion` runs *after* the coroutine has already
terminated, it races with Wire's own synchronous `invokeOnCancellation`, and it forces the call
object to be hoisted out of the frozen `VerifyPhoneNumber.kt` flow. We rely on structured
concurrency instead; `ConstellationRequestDispatcher` contains no `invokeOnCompletion` call, and the
only completion-time work it does (unlinking the Binder `DeathRecipient`) is done in a `finally`
block inside the coroutine body.

## Note on the blocking paths

The only other HTTP egress in this module is the same Wire gRPC client (`RpcClient`), always reached
through the suspending `execute` above. There is no separate blocking OkHttp path, no raw
`okhttp3.Call.execute()`, and no other HTTP client in `play-services-constellation`. The TS.43 /
service-entitlement verifier (`ts43/ServiceEntitlementExtension.kt`, `EapAkaService.kt`) is a
carrier-auth path that this change deliberately does not touch. If future work needs cancellable
blocking I/O there, the supported approach is the same structured-cancellation model (suspending API
+ `suspendCancellableCoroutine` with `invokeOnCancellation`), not an after-the-fact completion hook.
