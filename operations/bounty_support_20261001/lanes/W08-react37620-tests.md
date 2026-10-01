# W08 REACT37620-TESTS — support lane for W07 (react #37620)

Updated 2026-10-01. Support lane: no PR, no BountyHub claim and no upstream comment from this lane.

## Listing state

| Field | State |
|---|---|
| Listing | BountyHub cb7e2ac5, facebook/react#37620 |
| Advertised / funded / promised | $100 / $0 escrow / $100 promised (devlootxyz-bounties, per Slack inventory) |
| GitHub issue | OPEN, label `Status: Unconfirmed`, no maintainer comment |
| PR state (this lane) | none (support lane) |
| Competing upstream PRs | **#37694** (theworker02, opened 2026-09-26, OPEN, CLA pending at fetch time) and **#37705** (sidshehria, opened 2026-09-28, OPEN, CLA signed). Both are titled "Preserve SSR Suspense fallback across client re-suspend (#37620)", both include regression tests, and both say they claim the $100. |
| Claim state | none from this lane |
| Merge state | not merged |
| Payment state | not paid |

W07 should check these two PRs before submitting, since both already implement the same approach (keep the dehydrated fragment, hidden primary Offscreen, reuse the fallback sibling).

## Owned files

- `operations/bounty_support_20261001/lanes/W08-react37620-tests.md` (this file)
- `operations/bounty_support_20261001/lanes/W08-react37620-tests/ReactDOMFizzSuspenseFallbackHydration-test.js`: the test file, ready to copy into `packages/react-dom/src/__tests__/`
- `operations/bounty_support_20261001/lanes/W08-react37620-tests/patches/0001-Add-regression-test-for-Suspense-fallback-remount-on.patch`: `git am`-ready, against upstream main `7c6ac13e19fef500b7f669a16bbd01ecc95965ca` (2026-09-29). Author is woahwhattheheck (noreply). No trailers.
- `operations/bounty_support_20261001/lanes/W08-react37620-tests/experiment-24236-port-DO-NOT-SUBMIT.diff`: the throwaway reconciler experiment described below. Reference only.

Local branch: `~/work/react`, branch `fix-37620-fallback-remount-test`, commit `2d4892b5`. No fork exists yet, so nothing was pushed upstream.

Apply: `cd react && git am <commons>/operations/bounty_support_20261001/lanes/W08-react37620-tests/patches/0001-*.patch`

## (1) Regression test

File: `packages/react-dom/src/__tests__/ReactDOMFizzSuspenseFallbackHydration-test.js`. The name follows the `ReactDOMFizz*` convention for Fizz-streamed hydration tests (cf. `ReactDOMFizzShellHydration-test.js`). The harness is the self-contained `serverAct` pattern from that file, and the test is gated `@gate enableBrowserAPI`, like the existing `browser()` tests in `ReactDOMFizzServer-test.js`.

Scenario (mirrors the issue):
1. `ClientPromise` calls `use(ReactDOM.browser(...))` and then `use(getClientPromise())`, where the promise is cached at module level and created only on the client.
2. Fizz bails out of the boundary (`onBrowserBailout` fires once) and streams `<div><p>Loading...</p></div>` in a client-render state.
3. The test captures the server `<p>` node, attaches a MutationObserver and calls `hydrateRoot` followed by `waitForAll([])`.
4. Assertions: the visible tree is still `<p>Loading...</p>`; **the `<p>` is the same node** (`toBe(serverFallback)`); the MutationObserver did not record that node as removed.
5. Once the client promise resolves: the log is `['Loaded']`, `onRecoverableError` is not called, and the content is `<span>Loaded</span>`.

The test makes no assertion about whether a client `Fallback` fiber mounts. A correct fix may keep the dehydrated server fallback and never render the fallback component, so it only asserts on DOM identity.

### Result on current main (7c6ac13e), `yarn test`
Fails at the identity assertion, for the intended reason, in every channel I ran:

```
yarn test ReactDOMFizzSuspenseFallbackHydration                      # experimental
yarn test -r=stable ReactDOMFizzSuspenseFallbackHydration
yarn test -r=www-modern --variant=true ReactDOMFizzSuspenseFallbackHydration
yarn test -r=www-modern --variant=false ReactDOMFizzSuspenseFallbackHydration
yarn test --prod ReactDOMFizzSuspenseFallbackHydration

  ● ReactDOMFizzSuspenseFallbackHydration › keeps the server fallback when hydration suspends on a client promise after browser()
    expect(received).toBe(expected) // Object.is equality
    Expected: <p>Loading...</p>
    Received: serializes to the same string
    > 197 |     expect(clientFallback).toBe(serverFallback);
```
In other words, the content is identical but the `<p>` is a different node, which is the remount. ESLint is clean and Prettier left the file unchanged.

### Root cause path on main (for W07 and W15)
`packages/react-reconciler/src/ReactFiberBeginWork.js`:
- `mountDehydratedSuspenseComponent`: a `$!` (client-render) boundary is scheduled at `DefaultLane`.
- `updateDehydratedSuspenseComponent`, first pass: `isSuspenseInstanceFallback`, then `retrySuspenseComponentWithoutHydrating`. This calls `reconcileChildFibers(..., current.child, null)`, which queues the dehydrated fragment (and with it the server fallback DOM) for deletion. The browser() bailout uses `REACT_RECOVERABLE_DIGEST`, so no recoverable error is queued.
- The primary tree suspends on the client promise. The second pass takes the `else` branch ("Suspended but we should no longer be in dehydrated mode"), and `mountSuspenseFallbackAfterRetryWithoutHydrating` creates a **new** fallback fragment with `Placement` and deletes `current.child`. That is the remount.

## (2) What #24236 changed and why #24434 reverted it

**#24236** "Don't recreate the same fallback on the client if hydrating suspends" (gaearon; approved by acdlite and sebmarkbage; merged 2022-04-01 as `ebd7ff65b6fea73313c210709c88224910e86339`):
- Source changes (.new and .old forks):
  - `ReactFiberBeginWork`: one line, `renderDidSuspendDelayIfPossible()`, at the top of the same "Suspended but we should no longer be in dehydrated mode" branch, before `mountSuspenseFallbackAfterRetryWithoutHydrating`.
  - `ReactFiberLane`: replaced `includesOnlyTransitions` with `includesOnlyNonUrgentLanes(lanes)` = `(lanes & (SyncLane|InputContinuousLane|DefaultLane)) === NoLanes`.
  - `ReactFiberWorkLoop.finishConcurrentRender`, `RootSuspendedWithDelay`: `includesOnlyTransitions` became `includesOnlyNonUrgentLanes`. A suspended-with-delay render in any non-urgent lane (including hydration lanes) therefore **did not commit at all** and waited for data.
  - In 2022, `$!` boundaries were scheduled at `DefaultHydrationLane` (non-urgent). That is why the delay applied to them.
- Mechanism: the boundary never committed the client fallback. The whole root render for that lane was withheld, so the dehydrated server HTML stayed in place until the content resolved. If a new root update arrived, the fallback was recreated with the new props.
- Test changes it made:
  - Added 3 tests in `ReactDOMFizzServer-test.js`: "does not recreate the fallback if server errors and hydration suspends", "... and root receives a transition", "recreates the fallback if server errors and hydration suspends but client receives new props".
  - `ReactDOMHydrationDiff-test.js`: "warns when client/server renders an extra node inside Suspense fallback" became "does not warn ..." with snapshot `[]`. The recoverable "server could not finish this Suspense boundary" error was no longer logged while suspended, because fallbacks were not hydrated or committed.
  - `ReactDOMServerPartialHydration-test.internal.js` (SuspenseList "ALoading B" test): the expected recoverable-error log became `[]`.

**#24434** "Revert #24236" (gaearon, merged 2022-04-25 as `bd4784c8f8c6b17cf45c712db8ed8ed19a622b26`; commits `02e1722f` revert and `d7a9ef36` "Use @gate FIXME"):
- Reason, quoted verbatim: "It seems to be the cause of a late mutations regression on WWW. We don't know why but we should revert to unblock the next syncs."
- What broke: an internal Meta (www) production metric, **late mutations**, regressed. No public issue, OSS test or app was named, and no root cause was ever published. No OSS test failed. The revert restored the HydrationDiff and PartialHydration expectations and kept the 3 new tests under `// @gate FIXME` ("Disabled because of a WWW late mutations regression. We may want to re-enable this if we figure out why."). `includesOnlyNonUrgentLanes` was kept because `useDeferredValue` had adopted it.
- Inference (not stated by Meta): the likely mechanism is that #24236 suppressed the commit of the **entire root render** in non-urgent/hydration lanes whenever any client-render boundary re-suspended. Other work in that same render (sibling boundaries, effects, event-replay readiness) was held back with it, and the DOM mutations landed late. A fix that keeps the server fallback **locally**, at the boundary, without blocking the root commit avoids that class of problem. #37694 and #37705 both take that local approach.

Those 3 tests are still `@gate FIXME` on main (lines ~3536, ~3621 and ~3720 of `ReactDOMFizzServer-test.js`), and they still fail on main, which is the gated-expected state. If W07's fix makes them pass, jest reports `[GATED, SHOULD FAIL]`, and W07 must remove the `@gate FIXME` lines in the same PR.

### Experiment: naive port of #24236 onto current main (do not submit)
`experiment-24236-port-DO-NOT-SUBMIT.diff` (reverted locally afterwards):
- (A) delay line plus `includesOnlyNonUrgentLanes` in `finishConcurrentRender`, with the lane left at `DefaultLane`: **no effect**. The new test still fails at the identity check, because `$!` boundaries now render in `DefaultLane`, which counts as urgent, so the placeholder commits.
- (B/C) moving `$!` boundaries back to `DefaultHydrationLane` (with or without the delay): **the new test hangs with `RangeError: Potential infinite loop: exceeded 6000 iterations` in `renderRootSync`** plus repeated "Unexpected Fiber popped."
- The full port (A plus the lane change): the 3 `@gate FIXME` tests pass (`[GATED, SHOULD FAIL]`), but the `browser()` + client-promise case loops as in (B/C).
- Takeaway for W07: restoring the 2022 mechanism does not port. It either does nothing or hangs this exact repro, and it reintroduces the root-wide commit suppression suspected in the late-mutations regression. A boundary-local preservation of the dehydrated fallback is the viable direction.

## Requirements for W07's fix
- The new test passes in experimental, stable, `www-modern --variant=true/false` and `--prod`.
- If the 3 `@gate FIXME` tests in `ReactDOMFizzServer-test.js` start passing, remove their gates.
- These must stay green: `ReactDOMHydrationDiff-test.js` ("warns when client/server renders an extra node inside Suspense fallback"), `ReactDOMServerPartialHydration-test.internal.js`, `ReactDOMFizzServer-test.js` (`browser()` tests and the props-change recreate case), and `ReactDOMServerSelectiveHydration-test.internal.js`.
- A root update that changes the fallback props must still recreate the fallback (the third FIXME test covers this).

## Blockers
- None for this lane's deliverable.
- Upstream submission belongs to W07. Fork `woahwhattheheck/react` did not exist at session start (per orders).

## Next action
W07: `git am` the patch onto the fix branch and decide how to position against the open #37694 and #37705. If the fix lands as a separate commit, keep this test in the same PR.
