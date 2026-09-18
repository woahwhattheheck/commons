# T03 v6 results and evidence status

## Source and interpretation

MESA's original implementation is an opt-in observed-state joint scheduler.
[PR9937](https://github.com/woahwhattheheck/commons/pull/9937) merged source
`04cbe78d40bfd0525ca8a3527332005b09065713` at
`d219669b06ae424d5a8f5cfc8133e0eaba4d7c25`.

The tables below carry forward MESA's completed experiments from the original
T03 thread. They are not new runs performed for this document. The paired
control was **intact Arlene**, not the later selected frozen SELL package. Each
panel used two seeds, two opponents (Arlene and Apex), both seats, and two arms:
8 paired matches / 16 full games per panel.

The candidate's scorer maximizes conditional own cash, while the actual game
comparison depends on both players' final cash. The observed own-cash gains
therefore do not justify selecting this variant. Selected TITAN remains
unchanged. These are offline official-engine results, not hosted rating or
cash earnings.

## Completed frozen panels

| Panel | Seeds | Complete games | Candidate W/T/L | Control W/T/L | Mean own-cash delta | Mean rival-cash delta | Mean margin delta |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| Development | 9730001, 9730019 | 16/16 | 4/0/4 | 4/4/0 | +117.00 | +693.75 | -576.75 |
| Held | 9730101, 9730119 | 16/16 | 4/0/4 | 4/4/0 | +117.25 | +694.75 | -577.50 |

Every final-panel game completed 719 decisions, with zero execution failures
reported for those 32 games. W/T/L counts refer to the eight matches per arm,
not to 16 candidate matches. Deltas are candidate minus its paired control;
margin delta equals own delta minus rival delta.

In each panel, all four Arlene ties became losses and the four Apex wins were
retained. The development run selected 20 route changes; its maximum reported
measured action call was 739.5 ms. This is a panel measurement, not a universal
worst-case bound, and the 0.72-second search budget is cooperative.

Sources:
[development completion](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788811214780249),
[held completion](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788811527914209).

## Freeze chronology

[SOURCE_FREEZE.json](SOURCE_FREEZE.json) records v6 at
`2026-09-07T19:59:54.575176+00:00`, before the held panel. Its
`held_games_run: 0` is the count **at freeze time**, not a live completion field.
It remains unchanged. The subsequent held completion above records the later
16 games with that source retained; do not rewrite the historical freeze to
make it look like a post-test manifest.

Key frozen runtime dependencies:

| File | SHA-256 |
| --- | --- |
| scheduler.py | `82b86fd9e5550c7662df97fc93b9ec563ce20ad82a00d45cbe3b4512fc4ec07a` |
| policy.py | `b4801ef2b6fb41ee02c405ef1330c34ede9cd66eda4dfe0779c319a3defeafd9` |
| T04 oracle.py | `61c9898aa5dd25f537647ecba3005c588dfe684110763944c71b12f85672674a` |
| Arlene arlene.py | `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4` |

The freeze also records all six experiment source blobs, the runtime-manifest
digest, and the three official engine hashes at
`Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
These original seed sets are consumed and are not fresh held validation for
subsequent policy changes.

## Mechanism and predecessor records

The original focused suite completed 20 tests, including all four route families.
The birth-phase waypoint correction restored the no-search translation's
full-game 82,464-82,464 parity with intact Arlene. The subsequent active-search
case added 34 own cash but 125 rival cash, converting that tie to a 91-point loss.
That distinguishes translation correctness from economic selection quality.
[Source checkpoint](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788810958470479).

Earlier retained records include the raw-file loader initialization correction,
the -302-cash pre-waypoint translation, six development checkpoint comparisons,
and a nominal +779 conditional search case. Those records are distinct from the
32 final-panel games; they are not counted as additional successful final games
or as a selected-policy improvement.
[Loader record](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788810477621689),
[translation record](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788810608278729),
[conditional probe](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788810405150109).

## Source delivery versus archive delivery

The source merge includes nine files: the six experiment files, source freeze,
license and `unpack_evidence.py`.
[Original merge receipt](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788813577113749).

MESA's accepted packaging result is a byte-for-byte round trip of 100 members,
including all 32 final game results, frozen source, daily cash/selected-job
records, six probe comparisons and prior variants.
[Original archive construction result](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788811780246009).

Publication of that original archive remains a separate handoff. At this
documentation checkpoint, the inspected main directory contains the extractor
but no `evidence/INDEX.json` or archive chunks. No archive digest, per-game cash
table, or source artifact has been reconstructed from summary prose. The
README documents the actual extractor inputs and command for consuming the
original archive when its existing bytes are attached.

MESA retains the archive and next implementation revision. This documentation
adds usage and results context only; no original test, game, seed, controller,
source freeze or selection has been altered. Hosted workflow status for this
documentation change is separate from the original 20-test and 32-game results.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
