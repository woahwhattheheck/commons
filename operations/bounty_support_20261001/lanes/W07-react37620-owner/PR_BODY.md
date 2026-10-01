Title: Keep the server Suspense fallback when browser-only content suspends on the client

## Summary

Fixes #37620.

When a component calls `use(browser())`, Fizz emits its Suspense boundary as a client-rendered fallback (`<!--$!-->`). On the client, `updateDehydratedSuspenseComponent` retries the content without hydrating (`retrySuspenseComponentWithoutHydrating`). If that render suspends again, for example on a promise created on the client (`setTimeout`, `localStorage`, IndexedDB), the second pass goes to `mountSuspenseFallbackAfterRetryWithoutHydrating`. That deletes the dehydrated fragment, which holds the server fallback DOM, and inserts a newly created, identical client fallback, so CSS animations restart and DOM state is lost. `/server-promise` in the issue's repro doesn't hit this because the client render doesn't suspend.

This change keeps the boundary in the dehydrated state instead, leaving the server fallback in place until the content can render. The dehydrated state is the one pending boundaries already use: the rest of the tree commits normally and the retry listener is attached in the commit phase. Only this one boundary is affected. #24236 (reverted in #24434) took a different route: it held back the whole commit for non-urgent lanes.

The server fallback is kept in the second pass only when all of these hold:
- The boundary is a client-render fallback from a `browser()` bailout (recoverable digest).
- Neither the props, legacy context nor any context propagated into the boundary changed (`!didReceiveUpdate`, and no context lanes on the boundary). To make the context check work, the first pass propagates parent context changes before it drops the dehydrated fragment.
- The content didn't spawn a deferred render (`useDeferredValue`). That lane is only scheduled by the regular fallback path.

If any of these fails, the existing path is used: the client fallback is rendered and replaces the server one.

Making the kept boundary behave like other boundaries showing a fallback:
- It gets a new `SuspenseState` with `retryLane: NoLane`. Once unblocked, it's retried at a normal retry lane, not at the hydration `OffscreenLane` (idle). Otherwise the content could wait behind an unrelated suspended transition.
- `completeDehydratedSuspenseBoundary` calls `scheduleRetryEffect` for kept `<!--$!-->` boundaries, so `ScheduleRetry` is honored. Skipped siblings are prerendered, and content that suspends the commit on a stylesheet is retried. Ordinary dehydrated boundaries are unchanged.
- `attemptEarlyBailoutIfNoScheduledUpdate` retries a dehydrated `<!--$!-->` boundary when a parent context changed. This mirrors what it already does for a client-rendered boundary showing its fallback, so a fallback that reads context, or content unblocked by it, isn't left stale.

Scope and limits:
- While the server fallback is kept it is not hydrated, the same as a pending `<!--$?-->` boundary. Event handlers and effects in the fallback don't run until the content renders, and a discrete event on it triggers a synchronous attempt to render the content. Hydrating the fallback itself would be a larger change.
- A re-render that creates a new Suspense props object, or any parent context change, falls back to the current behavior (one client fallback).
- Fallbacks from server errors (non-recoverable digest) keep the current behavior. Each client retry queues the "switched to client rendering" error again, so keeping them would report it more than once. I left a TODO.
- When the content finally mounts, it goes through `retrySuspenseComponentWithoutHydrating`. That is the same path browser-only content uses today when it doesn't suspend on the client.

## How did you test this change?

Added tests to `ReactDOMFizzServer-test.js`, next to the existing `browser()` test:
- `keeps the server fallback if browser-only content suspends on the client`: the issue's shape. `use(browser())`, then `use()` of a promise created on the client. Asserts that the server `<p>` is the same node after hydration and is never removed (MutationObserver), and that the content replaces it once the promise resolves, with no recoverable errors.
- `replaces the server fallback if its props change while browser-only content is suspended`
- `updates the server fallback if a context it reads changes while browser-only content is suspended`
- `renders browser-only content if a context change unblocks it while the server fallback is kept`
- `reveals browser-only content without waiting on an unrelated suspended transition`
- `prerenders siblings of browser-only content while keeping the server fallback`
- `reveals browser-only content that renders a stylesheet while keeping the server fallback`
- `reveals browser-only content that only suspends on its deferred initial value`

On `main` without the reconciler change, the first six fail on the fallback node identity: `Expected: <p>Loading...</p> Received: serializes to the same string`, which is this bug. The last two pass on `main` and guard against regressing those cases. Each of the follow-ups listed above was added because one of these tests failed on an earlier version of this change.

Commands run on this branch:
- `yarn test` with `-r=experimental`, `-r=stable`, `-r=www-modern --variant=true`, `-r=www-modern --variant=false`, `-r=experimental --prod` and `-r=www-classic`. The suites run were `ReactDOMFizzServer`, `ReactDOMServerPartialHydration` (+`Activity`), `ReactDOMServerSelectiveHydration` (+`Activity`), `ReactDOMFizzShellHydration`, `ReactDOMFizzSuspenseList`, `ReactDOMHydrationDiff`, `ReactDOMFizzForm`, `ReactDOMFloat`, `ReactDOMSuspensePlaceholder`, `ReactDOMFizzDeferredValue` and `ReactDeferredValue`. Each configuration: 13 suites, 591 passed, 1 skipped.
- `yarn test -r=stable --ci packages/react-reconciler packages/react-dom`: 225 suites passed. 5387 tests passed, 21 skipped.
- `yarn test -r=experimental --ci packages/react-reconciler packages/react-dom`: 225 suites passed. 5388 tests passed, 21 skipped.
- `yarn linc`: passed. `yarn prettier`: applied.
- Flow: `flow full-check --merge-timeout 0` with each renderer's generated config found 0 errors for `dom-node` and `fabric` on the final commit, and for `dom-node`, `fabric`, `test`, `noop`, `custom`, `dom-browser`, `dom-fb`, `dom-legacy` and `markup` on the previous commit. The only difference between the two is one boolean condition and test changes. The default `yarn flow` merge timeout is too short for this machine.
