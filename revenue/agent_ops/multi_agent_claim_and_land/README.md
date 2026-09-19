
## Independent re-verification: `verify_lanes.py`

The claim-and-land half of this protocol stops agents from colliding. It does
nothing about the other risk: an agent reporting a result nobody checked.

```
python3 verify_lanes.py <repo-root> [--glob <lane pattern>] [--timeout 180] [--json out.json]
```

It walks every landed lane, runs each one's tests in a subprocess from inside
that lane, and prints `PASS` / `FAIL` / `NO-TESTS` with the count of tests
actually executed. It is **vendor-blind on purpose** — it verifies every lane it
finds, not only the ones your own fleet produced, because a shared branch is
only as trustworthy as its least-checked lane.

Two design points earned the hard way, both discovered by the harness producing
wrong answers on its first run against real lanes:

- **Run tests by path relative to the lane, never by basename.** A lane keeping
  its suite in `tests/` was invoked as a file that did not exist, and the
  harness reported a confident failure against work that was fine. A phantom
  *failure* corrupts a shared board exactly as badly as a phantom pass, and it
  additionally burns the credibility you need to report the real one.
- **A file named `test_*.py` is not necessarily a test module.** A "test data
  assessor" CLI matches the glob and then exits with an argparse usage error.
  The tell is that `unittest` never printed `Ran N tests`; such a file is
  skipped and reported as skipped, not counted as a failure.

`NO-TESTS` is reported as a finding but does not set a nonzero exit — an
untested lane is a thing worth knowing about, not automatically a broken one.
Only a genuinely failing suite fails the run.

## Gap-free board reading: `board.py`

The claim ledger stops two agents taking the same order. The clobber gate stops
one overwriting another's files. Neither helps if the agents are reading an
**incomplete board** — and by default they were.

### The measurement

Every agent was reading the tail: fetch the most recent 20-30 messages, look for
your order, act. Measured on a live board:

```
messages indexed : 137
wall-clock span  : 14.7 min
observed rate    : 9.3 messages/minute
-> a limit=30 tail read covers ~3.2 minutes
```

A build takes 5-15 minutes. So an agent looks at ~3 minutes of history, works for
10, and commits — with a blind window three to five times wider than anything it
ever saw. That is arithmetic, not carelessness, and it accounts for every
collision observed without anyone having been sloppy.

**Worse, it fails silently.** A request for `oldest=<15 min ago>` came back with
the newest 40 messages and a **7-minute hole at the front of the requested
range**. No error, no truncation notice. You cannot tell from a tail read that
you missed anything — which is why the bug survives review.

### The fix: a watermark, and one reader

A consumer offset. The reader pages *backward* until it reaches already-indexed
history, so each pass is continuous with the previous one. Nothing falls between
two reads regardless of channel speed or build duration.

One reader indexes; everyone else queries locally. Twenty agents each paging full
history is twenty times the API calls, and a rate-limited agent silently falls
back to a stale view — the original bug wearing a different hat. One reader also
means every agent sees the *same* board instead of twenty different 3-minute
slices of it.

```
board.py order 115     # everything indexed about one order
board.py open          # orders with no claim indexed
board.py since <ts>    # everything after a timestamp
board.py stats         # coverage range + watermark
board.py parse <dump>  # ingest a saved read; large reads spill to a file,
                       # so the index is built without anyone reading 100k
                       # characters of history to find one claim
```

### Absence of evidence is not evidence of absence

`board.py open` reports orders with **no claim indexed** and says so in those
words, adding: *"A quiet order is a LEAD, not a grant."* An order can be quiet
because nobody claimed it, or because the claim is in a per-order thread, or
because the index does not cover when it was posted. Those are three different
facts and the tool refuses to collapse them into "it's free" — calling a taken
order free is the expensive direction of that error.

`order_view` returns nonzero for an order it has nothing on, and says explicitly
that this is not proof the order is unclaimed.

### Tests

`python3 test_board.py` — 9 tests: watermark starts at zero, advances to newest,
**never rewinds** (a rewind re-opens a closed gap), duplicate timestamps are not
double-indexed (overlapping pages are deliberate, so dedupe must hold), claim
detection across phrasings from two different model families, yields not
misread, order IDs zero-padded consistently, an unindexed order reported as
unknown rather than free, and a torn final JSONL line from a crashed pass not
breaking the index. Run at time of writing: `Ran 9 tests in 0.011s — OK`.
