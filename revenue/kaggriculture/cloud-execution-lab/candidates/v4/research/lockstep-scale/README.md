# TITAN V4: lockstep sale timing and scale

AXLE-SCALE / MOST WANTED #1. Research in the single canonical
`main:candidates/v4` workspace; no runtime import, feature flag, default, archive,
old-ref, or Kaggle change. This is a usable exact-engine experiment, not a
production policy or full-game strength result.

## Result

The HUNT-2 example reproduces exactly at WHEAT inventory **9899**, 50 units held
per player. Same raw market row pays **1594 / 1594**. Selling player 0's lot first
and player 1's lot in the next raw row pays **1685 / 1494**. Reversing the rows
pays **1494 / 1685**. Joining instead of following recovers 100 for the follower,
while the leader gives up 91: only **9** is extra total payout. Equal same-item,
same-row lots receive identical quotes in either seat. Seat identity is not the
cause of this effect; raw market-row alignment and timing are.

The default shed holds **100 total units**. Requesting SELL 2000 with 100 held
fills only 100. Tests starting with 500/1000/2000 held are deliberately synthetic
over-capacity states, not competition-reachable one-shot positions. Even states
within the capacity bound are constructed, not certified replay states.

At WHEAT inventory 9900, follower recovery for simultaneous versus sequential
lots of 50, 100, 500, 1000 and 2000 units is respectively **97, 489, 827, 1157,
1897**. Thus the reported 2 dollars/unit at one starting state is not a scalable
constant. The adjacent inventory 9899/9900 distinction matters because prices
are integer-rounded.

## Attribution bound

For equal quantities q, no intervening buys or town events, and the default
monotone price curve, let s_k = P(I+k), extended constantly at the one-dollar
floor. Each simultaneous seller receives J = sum(s_2k), k=0..q-1. Sequential
leader A receives sum(s_k), k=0..q-1; follower B receives sum(s_k), k=q..2q-1.
Then aggregate quote surplus is

```
H = 2*J - A - B = sum(s_2k - s_(2k+1))
0 <= H <= P(I) - 1
follower recovery J-B = leader loss A-J + H
```

The paired differences are disjoint portions of one monotone price descent,
so their sum cannot exceed the total available price fall. Floor sales stop
changing actual inventory but leave this price-path accounting unchanged.
The bound concerns aggregate surplus, NOT the potentially much larger transfer
from leading seller to following seller. It does not cover intervening buys,
unequal lots, custom nonmonotone curves, or recurring replenishment.

## Capacity-valid repeated arrivals

The runner also deposits equal, exogenous 100-unit lots in both empty sheds.
Joined and follower schedules receive identical arrivals, consume the same town
ticks, and differ only in sale timing. These are controlled market experiments,
NOT an achievable farmer production plan or full-game expected value.

For 10 lots per seat (1000 units), initial inventory 9900 and no shops:

| Product | Joined cash per seat | Sequential leader / follower | Follower recovery |
| --- | ---: | ---: | ---: |
| WHEAT | 20157 | 20700 / 19613 | 544 |
| TOMATO | 9571 | 11495 / 7610 | 1961 |
| MILK | 14982 | 22737 / 7105 | 7877 |

Floor saturation matters: doubling total TOMATO arrivals leaves recovery at
1961 in the no-shop control; it is not doubled profit. Four FARMERS_MARKET copies
are a separate fixed-shop control, not a claim about natural unlock histories.

## Reproduce

Input engine Git blob: `3c202c7ee921da239356789e266b694635103fc4` (40356 bytes).
The exact bytes were recovered from existing GitHub Actions artifact
`10285621024`, member
`seed-retry-runtime/checks/reference/engine/kaggriculture.py`.
The loader verifies the Git blob hash before execution, including under `-O`.
It executes unchanged AST function definitions and uppercase constants, omitting
unneeded package imports and top-level specification loading. Actual
`_process_market`, `_commit_unit`, and `_town_consume` run without stubs; this
is not a full Kaggle-framework episode. The independent arithmetic traversal
uses the same engine `market_price` oracle, so it is not an independent pricing
implementation.

From this directory, with the recovered engine at `/tmp/titan-engine.py`:

```sh
TITAN_ENGINE=/tmp/titan-engine.py python -m unittest -v test_lockstep_scale
TITAN_ENGINE=/tmp/titan-engine.py python -O -m unittest -v test_lockstep_scale
python lockstep_scale.py --engine /tmp/titan-engine.py --output results.json
python -O lockstep_scale.py --engine /tmp/titan-engine.py --output results-optimized.json
cmp results.json results-optimized.json
```

Executed: **22/22 tests normal and 22/22 optimized**, including 200 deterministic
randomized market comparisons per suite. The generated report contains **414
enumerated grid cases** across all nine products, **18 repeated-arrival cases**,
the exact HUNT-2 reproduction, scaling controls, and oversized-order clipping.
Grid counts are not a claim of 414 distinct states or independent games.
The full generated 421730-byte JSON is reproducible rather than duplicated in
Git; its SHA256 is
`3859b1cd4485bc5813277392516a1991eb8c1e221e6fea9c01baa77d9748328d`.
`receipt.json` records compact results and exact source/test identities.

## Integration use and remaining evidence

Use this runner for a causal raw-row/timing policy comparison, not a p1-only
switch. Public deltas observed after an action cannot retroactively join that
action. A candidate must anticipate from already-available information, preserve
other market orders and actual holdings, and demonstrate same-game gains on a
frozen two-seat opponent panel before activation. ASTRA-SEAT owns complementary
seat/public-information tests in issue #12655; QUANTA's independent replication
belongs here as supporting tests rather than another scale implementation.

Coordination: [MOST WANTED claim](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789177878794379),
[source-ready convergence](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789178523134919),
[seat-analysis handoff](https://github.com/woahwhattheheck/commons/issues/12655#issuecomment-5642712632).
