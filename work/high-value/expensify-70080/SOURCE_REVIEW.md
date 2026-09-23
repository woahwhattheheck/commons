# Expensify #70080 — current-main scroll-restoration source review

Status: **pre-assignment source review only**. No upstream PR, Upwork application, /claim, or payout claim was created from this lane. A live >50-report UI reproduction was **not** performed from this seat.

## Pinned state

- Upstream: `Expensify/App`
- Issue: `#70080` — “[$250] Reports - Back button on report view returns to different scroll position”
- Upstream main: `dd0e8b65546b6e2e8914e74c535da26cd85dacc5`
- Related pagination PR: `#100144`, merged; head `f4f83e5d5881e10fb79de56c13f99e1f23ff99b8`, merge commit `cbc01867b06c84782e9e9a440bc59543a1a990bb`

## What #100144 already owns

Current `src/components/Search/index.tsx` (blob `aea1479aff194d4bcf351248e44d1f11a01406a8`) keeps a `wantedOffsetRef`, derives the next page from the server snapshot cursor, and re-arms a displaced page when a first-page response moves the server cursor below local `offset`. That is a **pagination/data recovery** mechanism.

A #70080 fix should not add a second pagination state machine to scroll-restoration code.

## Remaining source-level gap on current main

`src/components/Search/primitives/useScrollRestoration.ts` (blob `bde2735613044902a83177e648fc505dded34059`) does exactly one restoration attempt:

1. Read the route-keyed saved offset on focus.
2. Wait one `requestAnimationFrame`.
3. Call `scrollToOffset({offset, animated: false})` once.

There is no pending target, no retry when content grows, no “target became reachable” signal, and no user-interaction cancellation.

That is independently consistent with the issue’s >50-row symptom after #100144: data can recover after the one-shot restoration has already clamped against the currently reachable list extent.

## Distinct integration edge: cancellation cannot safely use ordinary onScroll

The safe behavior discussed in the issue is “keep restoration pending while data/layout recovers, but stop fighting the user once the user manually scrolls.”

Current Search list plumbing does **not** expose the two events that cleanly distinguish those responsibilities:

- `src/components/Search/SearchList/BaseSearchList/types.ts` (blob `c18b7a1719df8b455e4d15551310eef88c8274e1`) picks `onScroll`, but not `onScrollBeginDrag` or `onContentSizeChange`.
- Web `BaseSearchList` blob `5f7273b9f6f8271ca2a7e35ee64d4165c4e14060` forwards `onScroll`, not those events.
- Native `BaseSearchList` blob `8164250b667d1fba56d3992f6ba0b60f19ce18cb` has the same boundary.

That matters because `scrollToOffset()` is itself a programmatic scroll and can produce scroll events. Cancelling the pending restore from ordinary `onScroll` risks treating the restoration’s own movement as user intent and cancelling itself.

The narrow event contract should therefore be explicit:

- **retry signal:** list content/layout growth (prefer `onContentSizeChange`, or an equivalently precise reachability signal);
- **cancel signal:** direct user gesture (prefer `onScrollBeginDrag` / equivalent interaction event), **not generic `onScroll`**;
- **route/query change:** invalidate the old pending target;
- **programmatic restore:** must never be classified as manual cancellation.

`useSearchListViewState` (blob `d135ea73eafcd214c7d5405d1ac732d725c7088d`) is the common owner of the FlashList ref and invokes `useScrollRestoration` for flat, grouped, report, chat, and task Search views, making it a natural place to bind a shared restoration contract without duplicating it per view.

## Recommended ownership split

1. Keep `Search/index.tsx` / #100144 responsible for missing-page recovery.
2. Keep `useScrollRestoration` responsible only for a route-scoped pending visual target.
3. Extend the shared list event surface to carry a content-growth callback and a real-user gesture callback.
4. Retry only after a meaningful reachability/content-growth event; do not poll every frame.
5. Clear the target after a successful reachable restore, on direct user drag, on route/query identity change, or once the list is terminal and the target is provably unreachable.
6. Cancel any queued animation-frame callback in focus cleanup so stale focus work cannot fire after the route loses focus.

## Acceptance fence

Before implementation is accepted, the selected contributor should prove both parts independently:

- #100144 recovers the needed >50-row data in the plain back-navigation path; and
- restoration retries only when the list can make progress, without fighting real user input.

This review does **not** claim the issue is currently reproducible in a live account; recent issue comments contain mixed retest results. It narrows the source contract that should be tested if Expensify assigns the work.
