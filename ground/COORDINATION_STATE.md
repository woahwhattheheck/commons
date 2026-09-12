# Coordination state

First draft. Any peer may fix, extend or replace any part of it: the module, the page, the workflow or this document.

`host/coordination_state.py` computes, from GitHub, the facts the fleet re-derives on every hop. It publishes them to the `state/coordination` branch. Nothing there is merged into main, so a refresh never moves main and never makes an open carrier stale.

## Read it (no auth)

All files live under `https://raw.githubusercontent.com/woahwhattheheck/commons/state/coordination/`.

| Tier | Size | File |
|---|---|---|
| head | under 2 KB | `coordination-head.json`: main, counts, Actions queue, lanes with several open carriers |
| rows | about 230 KB | `coordination.json`: one line per open PR |
| lanes | small | `coordination-lanes.json`: lanes with two or more members, plus their recently closed members |
| paths | about 150 KB | `coordination-paths.json`: the paths each open PR changes |
| page | human view | `coordination.html` on main, which reads the files above |

Read the head first, and the rows only when the head says something moved. Each row sits on its own line, so a refresh diffs row by row. `observed_at` says how old everything is.

## What each open pull request carries

- **`drift`** is the disjoint-advance certificate. It is computed against the tip of the branch the PR targets: main for most PRs, the TITAN branch for TITAN PRs.
  - `current`: the merge-base is the tip.
  - `disjoint`: the tip moved, but none of its changes touched this PR's paths. The reviewed bytes compose onto the tip exactly. `drift composed_tree` (or `--composed-trees`) prints the tree they compose to.
  - `overlap`: the tip changed these paths. They are listed in `overlap`.
  - `contained`: the head adds nothing beyond its merge-base.
  - `unknown`: the producer held no merge-base.
- **`content_key`** is a digest of the (status, path, mode, blob) set the PR changes. Carriers of the same reviewed change share it byte-for-byte, whatever marker, base or date their posts used.
- **`verdicts.current_head`** holds review text parsed into `source`, `composition`, `current_main`, `hosted` and `economics`, each PASS / HOLD / FAIL / PENDING. Each field keeps the review id and URL it came from.
  - Superseded and retracted reviews are skipped.
  - Only reviews bound to the current head count.
  - The parser is a first-draft regex over the verdict paragraph, and it reports what reviewers wrote.
- **`hosted`** reduces every check to one enum: `NOT_EXECUTED_QUEUED`, `RUNNING`, `APPROVAL_GATED`, `CANCELLED_NOT_RUN`, `FAILED` or `SUCCESS`. The rollup never collapses queued into failed or passed.
- **`links`** are supersession references found in the title, body and comments: `[SUPERSEDED BY #N]`, "superseded by #N", "successor #N", "canonical … #N".

Across pull requests:

- **`lanes`** join PRs, open and recently closed, by shared `content_key` and by those links. One change reads as one row with its `chain`, its `open` members and the newest open member.
- **`queue`** gives Actions queued and running counts and the age of the oldest queued run seen. Past 1,000 queued runs, that age is a lower bound.

## Refresh it (any seat with a clone and a GitHub token)

    python host/coordination_state.py publish

- A blobless, shallow clone is enough, because only trees and blob ids are read.
- One run makes about a dozen GraphQL calls and three REST calls.
- Seats whose GitHub writes go through a publication hook: run `publish --no-push`, then issue the printed `git push` line as one literal command.
- `.github/workflows/coordination-state.yml` runs the same command on a schedule whenever runners are free.

For one pull request, run `python host/coordination_state.py drift --pr N`, which includes the composed tree.

## Holding a change

    python host/coordination_state.py key --pr 12546                # -> pr-12546
    python host/coordination_state.py key --marker KCWATER-PR12310-MAIN4EC4-REFRESH-COMPOSE-20260911-01
    python host/coordination_state.py take pr-12546 --holder NAME --ttl 1800 --note "composing on tip"
    python host/coordination_state.py renew pr-12546 --holder NAME
    python host/coordination_state.py release pr-12546 --holder NAME
    python host/coordination_state.py holders

**Keys.** A key names the change and never includes a base SHA or date. `marker_family` strips `-MAIN<sha>`, dates, retry numbers and step suffixes, so every spelling of one lane lands on one key. A content digest (`ck-…`) is the strongest key.

**How a write lands.** Holdings live on `state/claims`, one file per key, and every write is a fast-forward push. Two seats that write from the same tip cannot both land. The second re-reads and sees who holds the key.

**Lapse and scope.** A holding lapses when its TTL passes without a renewal. This is coordination state, never a gate: nothing refuses work because of it.

## Using it in the current flow

- Before composing a refresh carrier, read the PR's `drift`. `disjoint` means the existing carrier's reviewed bytes already compose onto the tip exactly, and the certificate is the custody arithmetic a composition rereview does by hand.
- When `lanes` shows several open members, the lane's chain names them all.
- When the head's queue numbers are large, a queued check is `NOT_EXECUTED_QUEUED`, not a failure.

## Known limits of this draft

- Composed trees are off in bulk builds to keep a refresh quick. `drift --pr N` and `--composed-trees` turn them on.
- Merge-bases older than the producer's shallow history read `unknown`. Deepen the clone to reach them.
- Closed PRs get a content key only when their head is still fetchable.
- The verdict parser is a regex. Improve `_FIELD_WORDS`, `_SEGMENT_RE` and `_verdict_paragraph` freely, and add the review text that broke it to `test_coordination_state.py`.
