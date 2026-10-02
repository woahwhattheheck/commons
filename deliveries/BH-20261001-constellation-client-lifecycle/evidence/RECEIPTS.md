# Build & test receipts

Real runs in this container. No results are asserted that were not produced by an actual run; the
raw logs and JUnit XML are included so the counts can be checked independently.

## Environment

- JDK 21.0.11 (OpenJDK), Gradle 8.13 (wrapper), AGP 8.13.2, Kotlin 1.9.22
- compileSdk 35, build-tools 35.0.0 (installed via `sdkmanager`), minSdk 19, targetSdk 29
- coroutines 1.7.3, coroutines-test 1.7.3, Wire 6.2.0, OkHttp 4.12.0, mockito-core 5.11.0
- Module/task: `:play-services-constellation-core:testDebugUnitTest` (host JVM unit tests)

## Command

```
GRADLE_MICROG_VERSION_WITHOUT_GIT=1 \
  ./gradlew --no-daemon --no-configuration-cache --console=plain --max-workers=1 \
  :play-services-constellation-core:testDebugUnitTest
```

Environment notes (honest, these are container constraints, not changes to the project):
- `GRADLE_MICROG_VERSION_WITHOUT_GIT=1` is the project's own toggle (root `build.gradle`) for
  building from a checkout without git tags — required because the source was obtained as a shallow
  clone. It only affects the computed `versionName`/`versionCode`, nothing under test.
- `--no-configuration-cache`: the configuration cache hit a serialization incompatibility with this
  AGP/KGP combination (`BuildToolsApiClasspathEntrySnapshotTransform`), unrelated to this change.
- `--max-workers=1` and retries: Maven Central intermittently returned HTTP 429 through the sandbox
  proxy while first populating the dependency cache; throttling + retry resolved it. Once cached,
  runs are clean (~32–36s).

## pass-after (fix in place) — `pass-after.log`

```
BUILD SUCCESSFUL in 36s
```

| Suite | tests | failures | errors |
|---|---:|---:|---:|
| ConstellationCallbacksWrapperTest | 5 | 0 | 0 |
| ConstellationRequestDispatcherTest | 4 | 0 | 0 |
| verification.MtSmsInboxScopeTest | 7 | 0 | 0 |
| proto.builder.SyncRequestPhoneNumberResolverTest (pre-existing) | 5 | 0 | 0 |
| verification.ts43.Fips186PrfTest (pre-existing) | 3 | 0 | 0 |
| **Total** | **24** | **0** | **0** |

JUnit XML: `evidence/test-results/`.

## fail-before (defects reintroduced) — `fail-before.log`

Applying `evidence/reintroduce-bugs.patch` to the fixed sources reintroduces the three original
defects (API unchanged, so the same test sources compile). Result:

```
BUILD FAILED in 32s
:play-services-constellation-core:testDebugUnitTest FAILED
```

5 failures, each on the test that targets a specific defect — and nothing else regressed:

| Failing test | Defect reintroduced |
|---|---|
| `MtSmsInboxScopeTest.dispose_cannotEraseANewerRequest` | MT-SMS inbox state made process-global again → "A's inbox was disposed when B started" |
| `ConstellationRequestDispatcherTest.callerDeath_cancelsTheRunningRequest_andUnlinks` | caller Binder-death linking disabled → "request should have linked to caller death" |
| `ConstellationRequestDispatcherTest.callerAlreadyDead_cancelsRequestImmediately` | death handling disabled → request job not cancelled |
| `ConstellationRequestDispatcherTest.failureInRequest_isContained_notPropagatedAsJobFailure` | coroutine-level containment disabled → failure surfaced as a job failure |
| `ConstellationCallbacksWrapperTest.runtimeExceptionFromCaller_isContained` | `RuntimeException` containment removed → `IllegalStateException` propagated |

JUnit XML: `evidence/test-results-fail-before/`.

The other 19 tests (including both pre-existing suites, the wrapper's RemoteException/cancellation/
pass-through/asBinder cases, the dispatcher's normal-completion case, and the other six MT-SMS scope
cases) stayed green under the buggy build — so each failure is attributable to the specific defect,
not collateral.

## Reproduce

```
# 1. source at the verified base
git clone https://github.com/nwinkelman2/gmscore && cd gmscore
git checkout 0266edd1694cbeac340b59d9287a50112465e0a4
# 2. apply the change
git apply /path/to/constellation-lifecycle.patch
# 3. pass-after
GRADLE_MICROG_VERSION_WITHOUT_GIT=1 ./gradlew --no-configuration-cache \
  :play-services-constellation-core:testDebugUnitTest          # BUILD SUCCESSFUL, 24/0
# 4. fail-before
git apply /path/to/reintroduce-bugs.patch
GRADLE_MICROG_VERSION_WITHOUT_GIT=1 ./gradlew --no-configuration-cache \
  :play-services-constellation-core:testDebugUnitTest          # BUILD FAILED, 5 discriminating failures
git checkout -- play-services-constellation/core/src/main      # restore
```
