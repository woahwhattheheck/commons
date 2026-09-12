# Alternate-day livestock feed candidate

Status: **candidate only / not selected by `TITAN-CONFIG.json`**.

## Engine receipt

`mechanics.py` is the repository's mechanically extracted Kaggriculture engine surface. Its animal daily refresh first updates `consecutive_unfed`, removes the animal only when the count reaches 2, and only then evaluates production. Therefore the first unfed refresh leaves the animal in place. On a due production day that surviving animal still receives the base `+1` yield. Feeding is separately required to consume a pending care bonus, and `cared_today && fed_today` is required to bank a new care bonus.

That makes one missed feed mechanically legal, but a blind every-other-day policy is not safe: a second miss escapes, and skipping a feed can destroy care value.

## Candidate boundary

`alternate_feed.py::propose_alternate_day_feed` is a bounded returned-action proposal. It changes only a successful `FEED` on step 23 of a standard 24-turn day, and only when all of the following are certified:

- the animal has `consecutive_unfed == 0`;
- it is not already fed, cared, carrying a pending care bonus, or receiving another actor's `CARE` this turn;
- the completed post-unit snapshot proves the incumbent `FEED` actually succeeded;
- the same animal has a reachable feed in the next day according to the existing physical feed-window route certificate;
- no unresolved route checkpoint, stock transfer, requested replenishment, or earlier wheat sale invalidates that future feed;
- observed wheat remaining after the current market row already covers the next-day feed obligation **without credit for the wheat saved by this candidate**; and
- retaining the saved wheat cannot overflow the shed at the daily inventory return.

Approved FEED actions become `PASS`; every other action and every market slot is preserved byte-for-byte by the proposal.

## Why the candidate is day-close only

The existing feed-window certificate crosses into the next day only from a day-close observation. Restricting the candidate to that boundary lets it reuse an already-audited physical route/input proof instead of inventing a second simulator or assuming tomorrow's requested purchases will arrive.

## Tests

`test_alternate_feed.py` covers the extracted engine invariant directly and then exercises the proposal's positive certificate plus rejection cases for prior starvation, current/pending care, duplicate service, failed incumbent feed, missing rescue, current/future wheat sales, route checkpoints, shed overflow, nonstandard clocks, and late-episode boundaries.

No canonical feature flag or release configuration is changed by this carrier. Promotion requires separate evaluator evidence and an explicit composition decision.
