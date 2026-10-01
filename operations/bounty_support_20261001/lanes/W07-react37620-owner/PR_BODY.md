Title: Keep server fallback when browser-only content suspends on the client

## Summary

Fixes #37620.

When a component calls `use(browser())`, Fizz emits its Suspense boundary as a client-rendered fallback (`<!--$!-->`). On the client, `updateDehydratedSuspenseComponent` retries the content without hydrating (`retrySuspenseComponentWithoutHydrating`). If that render suspends again, for example on a promise created on the client (`setTimeout`, `localStorage`, IndexedDB), the second pass goes to `mountSuspenseFallbackAfterRetryWithoutHydrating`. That deletes the dehydrated fragment, which holds the server fallback DOM, and inserts a freshly created, identical fallback. The fallback DOM is recreated, so CSS animations restart and any DOM state is lost. `/server-promise` doesn't hit this because the client render doesn't suspend.

This change adds a branch to that second pass. If the boundary is a client-render fallback from a `browser()` bailout (recoverable digest) and its props haven't changed, we:

- remove the dehydrated fragment from the pending deletions,
- restore the dehydrated `SuspenseState`, and
- complete it the same way as a dehydrated boundary that suspended during hydration.

That state already exists and is handled throughout the work loop. The rest of the tree commits normally, the retry listener is attached in the commit phase, and when the promise resolves the boundary is retried and the content replaces the server fallback.

How this differs from #24236 (reverted in #24434): that PR held back the whole commit with `renderDidSuspendDelayIfPossible` for non-urgent lanes. This change only affects the one boundary and never delays the root commit. It also doesn't depend on lanes, because the client render of a `<!--$!-->` boundary is scheduled at `DefaultLane`.

Scope and limits:
- If the fallback props change (for example a parent re-renders with a new fallback), the current behavior is kept: the client fallback is rendered and replaces the server one. There's a test for this.
- Boundaries whose fallback came from a server error (non-recoverable digest) also keep the current behavior. Each client retry queues the "switched to client rendering" recoverable error again, so staying dehydrated would report it more than once. I left a TODO. When I locally ungated the three `@gate FIXME` tests from #24236 with the boundary condition broadened to all `<!--$!-->` boundaries, this is exactly what failed: the error was reported twice. Their expected error message is also out of date.
- While suspended, the server fallback stays as server HTML (not hydrated), the same as a pending `<!--$?-->` boundary today.

## How did you test this change?

Added two tests to `ReactDOMFizzServer-test.js` next to the existing `browser()` test:
- `keeps the server fallback if browser-only content suspends on the client`: server renders the fallback because of `browser()`. The client then suspends on a promise created on the client. The test asserts the server `<p>` is the same node after hydration, and that it is removed and replaced by the content once the promise resolves, with no recoverable errors.
- `replaces the server fallback if its props change while browser-only content is suspended`.

Without the change to `ReactFiberBeginWork.js`, the first test fails: the fallback `<p>` is a different node with the same content ("serializes to the same string"). With the change, both pass.

Commands run:
- `yarn test -r=experimental` and `yarn test -r=stable` on `ReactDOMFizzServer-test.js`, `ReactDOMServerPartialHydration-test.internal.js`, `ReactDOMServerSelectiveHydration-test.internal.js`, `ReactDOMFizzShellHydration-test.js`, `ReactDOMFizzSuspenseList-test.js`, `ReactDOMServerPartialHydrationActivity-test.internal.js`: 561 passed on each channel.
- `yarn test -r=www-modern --variant=true` and `--variant=false` on the Fizz, PartialHydration and SelectiveHydration suites: 276 passed each.
- `yarn test --prod -r=experimental` on the same three suites: 276 passed.
- `yarn test -r=experimental packages/react-reconciler/src/__tests__/ReactSuspense`: 10 suites, 220 passed.
- `yarn lint`: passed. `yarn prettier`: no changes.
- `yarn flow dom-node` / `yarn flow-ci dom-node`: the only error reported is `Internal error: check job timed out after 100 seconds` in `packages/react-client/src/ReactFlightClient.js`. Unmodified `main` reports the same error on the same machine, and no type errors were reported.
