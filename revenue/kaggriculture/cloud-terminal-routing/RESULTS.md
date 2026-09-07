# Frozen v3 results

Source was frozen before any held game: see [FREEZE.json](FREEZE.json) and the
[contemporaneous Slack freeze](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788809618102709).
No runtime or measurement bytes changed during the held panel. All results use
the pinned unmodified official interpreter with passive measurement hooks and
fresh process-isolated actors, not a hosted Kaggle runner.

## Paired results

Each row represents **both seats**; money is reported as candidate/control own
money followed by the rival's, independent of the physical seat. Both seats
produced the same corresponding money values; no seat was omitted.

| Split | Seed | Opponent | Control own / rival | Candidate own / rival | Own delta | Margin delta |
|---|---:|---|---:|---:|---:|---:|
| Dev | 9750001 | Arlene | 90,439 / 90,439 | 90,509 / 90,345 | +70 | +164 |
| Dev | 9750001 | Apex | 91,625 / 82,567 | 91,625 / 82,567 | 0 | 0 |
| Dev | 9750019 | Arlene | 53,244 / 53,244 | 53,317 / 53,147 | +73 | +170 |
| Dev | 9750019 | Apex | 53,528 / 43,339 | 53,528 / 43,339 | 0 | 0 |
| Held | 9750101 | Arlene | 93,453 / 93,453 | 94,021 / 92,829 | +568 | +1,192 |
| Held | 9750101 | Apex | 95,852 / 80,266 | 95,852 / 80,266 | 0 | 0 |
| Held | 9750119 | Arlene | 89,882 / 89,882 | 89,987 / 89,768 | +105 | +219 |
| Held | 9750119 | Apex | 91,368 / 82,005 | 91,368 / 82,005 | 0 | 0 |

Development and held each contain 8 candidate games plus 8 paired control games.
Each candidate panel is 8W/0T/0L versus control 4W/4T/0L. In each panel four ties
became wins and four wins were retained. Mean own/margin deltas are +35.75/+83.5
for development and +168.25/+352.75 for held. All 32 selected/control games
completed 719 turns without an actor failure. All 16 paired pre-698 observation
and action hashes match, including the opening hires and input pickup.

Maximum selected actor call: development 0.055237434 seconds; held 0.050522863.
These child-measured timings are specific to the cloud host. The evaluator's
RPC limits and per-process resource samples remain in the raw records.

## What changed economically

Sold-unit totals are identical between arms in **all 16 pairs**. Final carried
inventories, shed contents and on-tile held yield are empty in both arms. There
are zero measured candidate DROP-loss units. Therefore these games do not
establish extra harvest or reduced stranded goods: the improvement is delivery
and sale timing under competitive prices.

For example, development9750001 against Arlene sells 78 CARROT, 3 EGG,
12 FERTILIZER, 6 MILK and 3 WOOL in both arms from decisions698–718. Actual
terminal receipts change from 4,536 to 4,606: CARROT4,009→4,109,
FERTILIZER36→44, MILK292→258, WOOL7→3, EGG192→192. Own gain is +70;
the rival loses94, so margin improves164. Both seats show this pattern.
Per-item cash and unit counts for every pair are in restored `RESULTS.json`.

The tests separately establish useful WATER, decay, four shed access tiles,
selective PLACE, real worker-order capacity, final-turn deposit/sale, visible
resource seeding, state-preserving execution and native loader behavior.
They do not turn this small panel into evidence against diverse opponents or
prove optimality on arbitrary farms. T08 composition requires its own ablation.

## Rejected development versions

The evidence retains the exact sources and recorded outcomes; do not promote
these older entry points accidentally.

| Version | Recorded pair | Outcome / cause |
|---|---|---|
| v1 | 9750001 vs Arlene, both seats | Two step-zero failures: native loader does not supply `__file__`. |
| v1b | Same pair | Two losses, margin −1,407. Stateless greedy planning disrupted productive treatment/collection; 46 carrots sold instead of 78. |
| v2 | Same pair | Two losses, margin −276. Persistent queues and treatment upgrades helped, but greedy route allocation still displaced parent value; 68 carrots sold. |
| v3 | Complete development and held panels above | Warm-start with the parent's feasible own known route; all eight Arlene ties across the two panels become wins. |

The initial multi-seed control invocation reached the container deadline after
four completed, persisted games. Its remaining controls were completed in
separately named files; any unrecorded in-flight work is not counted. There are
38 persisted experiment attempts: 32 selected/control games, four rejected-policy
losses, and two loader failures. The original records and hashes are preserved.

## Native package and local checks

15 engine/loader tests pass, plus compile checks. The native archive is40,440
bytes, SHA256 `4954c74023e06c34f5430a942898d691fe61afd77c1bd893d616c26ed3d3af9c`.
Two cold probes match the source's initial action. Four separate packaging games
(reference and actual extracted export, both seats on development9750001) have
identical complete trace hashes and scores. The maximum exported call is
0.066033608 seconds. Packaging replays are not independent held experiments.

## Raw evidence

Run `python evidence.py --output /tmp/t05-evidence` from this directory.
The lossless archive restores29 files /27,594,762 bytes, including the38 recorded
attempts, all final-day observations/actions, complete metrics, rejected sources,
`RESULTS.json`, four-game `export-check/report.json`, receipts and test logs.
Every restored byte stream was compared with its original. The index includes
the original file lengths and SHA256 values. Archive SHA256:
`b4905695d5c3c80a0f1e21eacc50c23c715c5a10a93aa41665a250720ce29147`.

No Kaggle submission, public notebook write, new spending, owner-PC computation,
leaderboard rating change or earned-payment claim is part of this delivery.
