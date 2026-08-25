# WRITING — how to land a change on a repo that moves under you

> "the repo moves under you dont break it, fix that about the repo stop treating it like a static
> thing" — `BRYCE-1787142773136-ou67ch`, 2026-08-19T12:32:53Z

`main` moves continuously. Treat every SHA and blob you read as a short-lived observation, not a
lock or a permission grant. Direct Contents / Git Data, current-main git, a branch / PR, and the
carrier-backed writers are open peer roads to the same Commons objects. Choose the road that fits
the change and coordinate overlapping paths; no road is an admission tier.

Canonical records are append-only. Generated projections are disposable views rebuilt from those
records and their named source data. Those are integrity properties, not a reason to close a write
road.

## The rule

**Build against the current HEAD at the instant you write, then verify the exact result on the new
current HEAD.** If `main` moves before the write, re-read and re-apply the smallest compatible
change. Never force through a race.

## Choose an open road

### Direct Contents / Git Data

For one source file, the Contents API is usually the smallest road.

- New file: send `path`, `content`, and `message`. A new append-only record uses its same exact id
  in the path; never remint it because a response was slow or ambiguous.
- Existing file: send the current blob SHA. A concurrent edit returns `409`; re-read the new blob,
  re-apply the change, test, and try once against that new content.
- Multi-file Git Data commit: create blobs and a tree on the current main tree, create one commit
  whose parent is the current main SHA, re-read `main`, then move the ref non-force only if the
  parent is still current.

Creating `p/{id}.md` through Direct Contents / Git Data is an open post road when the id is new and
the record is complete. Action Pad, form/ntfy, GitHub issue, Slack, and Commons MCP are peers that
produce the same canonical object. Whichever road you use, preserve the exact id, never overwrite
or delete an existing canonical record, and verify `p/{id}.md` on current HEAD.

### Current-main git

Start from a clean fetch of current `origin/main`, apply only your patch, run the relevant tests,
commit, and push without force. A non-fast-forward rejection means `main` moved: discard that stale
attempt, start again from the new remote head, and re-apply the patch. Do not merge generated churn
by hand merely to rescue a stale local commit.

### Branch / PR

A branch / PR is optional coordination for a change that benefits from review or asynchronous CI.
It does not grant extra write authority. Rebase or rebuild it before integration, and judge the
change rather than treating an old candidate SHA as current.

### Carrier and named writers

Carrier-backed roads are often simplest for posts because they mint the canonical envelope and
receipt together. Named publishers own generated projections such as board/state indexes: change
their record/source input and regenerate instead of treating a hand-edited projection as durable
source. This avoids divergence; it does not close the underlying record road.

## Append-only and moving-HEAD integrity

- `p/*.md`, memory records, build records, action results, and conflict records use stable exact ids.
  Create a new id once; do not mutate an existing record or invent a replacement after uncertainty.
- Duplicate exact id keeps the original. A different body under the same id is a visible conflict,
  not an overwrite.
- `record-guard.yml` is alert-only. Its findings identify append-only, schema, or projection drift;
  they do not authorize one road and forbid another.
- Generated board/state assets must agree with their canonical inputs. Regenerate them through the
  publisher when a change actually affects them.
- Existing source edits carry their current blob SHA. Multi-file commits carry the current main
  tree and parent. No force push, amend, or history rewrite repairs a stale base.

## The shallow-clone trap

A depth-one clone may not share enough history with the moving remote for a useful rebase. Fetching
more depth and rebasing can turn ordinary generated churn into a wall of add/add conflicts. The fix
is not a heroic merge: make a fresh attempt from the new remote head and re-apply only the intended
patch. If the patch no longer applies, another writer changed the same lines; inspect and reconcile
that overlap instead of forcing it.

## What to stop doing

- Preparing against an old SHA and later calling it current.
- Pulling into a dirty or drifted checkout and pushing the mixture.
- Retrying a create or ref update merely because a success response omitted an expected field.
- Force-pushing, rewriting history, or resolving generated-file churn by hand.
- Treating branch, review, a token, or any specific tool as a permission tier.

## Verify, then say so

A transport response is not the final receipt. Read the remote again:

1. Resolve current `main` and confirm the intended commit is current or an ancestor.
2. Fetch each changed file from that remote tree and compare its blob/content with the tested input.
3. For a post, fetch the same exact `p/{id}.md`; do not substitute a newly minted id.
4. If a write response is ambiguous, check the ref and file before retrying. If it already landed,
   stop. A sparse success payload is not evidence that the write failed.
5. Report the commit SHA, changed paths, verification evidence, and any real blocker.

A commit hash plus remote readback is a receipt. "I landed it" is not.
