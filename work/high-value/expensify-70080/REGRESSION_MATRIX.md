# Expensify #70080 — discriminating regression matrix

Pinned upstream main: `dd0e8b65546b6e2e8914e74c535da26cd85dacc5`.

These are proposed regression cases for the selected implementation. They are **not claimed as executed UI tests** by this seat.

| Case | Setup / event order | Expected invariant | What it distinguishes |
|---|---|---|---|
| R1 first-page restore | Saved offset is reachable at first focus frame | Exactly one non-animated restore lands at target | Preserves current happy path |
| R2 deep target + delayed growth | Saved target is beyond initial content; first restore cannot reach it; content grows after #100144 recovers rows | Target stays pending and is retried after growth; final visible position matches saved target | Core #70080 residual after pagination recovery |
| R3 programmatic scroll event | R2, but the programmatic `scrollToOffset` emits ordinary scroll events | Pending target is **not** cancelled merely by those events | Prevents self-cancellation |
| R4 manual drag wins | Restore is pending, then user begins a drag before content reaches target | Pending target is cancelled; later growth does not yank the list back | User agency / no scroll fight |
| R5 route/query identity changes | Restore pending for query A; Search switches to query/route B | A’s pending target is discarded and never applied to B | Prevents stale restoration |
| R6 zero offset | Saved offset is 0/undefined | No restore loop or synthetic movement | Existing guard stays intact |
| R7 terminal unreachable | Target is beyond available content and Search reports no more data | Restoration terminates without endless retries | Bounded failure behavior |
| R8 duplicate size callback | Same content extent is reported repeatedly | No redundant retry storm | Prevents render/event churn |
| R9 multi-page recovery | Target needs more than one recovered page; content grows in stages | Restore may re-attempt after meaningful growth but does not add its own Search pagination requests | Keeps #100144 ownership intact |
| R10 web/native parity | Run R2–R5 through both BaseSearchList implementations | Same cancellation/retry semantics | Ensures shared contract reaches both platforms |

## Test seam

A deterministic unit test can avoid a real network by using:

- a mocked FlashList ref that records `scrollToOffset` calls;
- a saved route offset;
- explicit “content grew” callbacks;
- explicit `onScrollBeginDrag` to model manual input;
- route/query identity replacement.

The most important hostile assertion is R3: **a programmatic restore must not cancel its own pending retry**. If cancellation is wired to the existing generic `onScroll` callback, this case should fail and expose the bug in the proposed implementation.
