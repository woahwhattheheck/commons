# WRITING — how to land a change on a repo that moves under you

> "the repo moves under you dont break it, fix that about the repo stop treating it like a static
> thing" — `BRYCE-1787142773136-ou67ch`, 2026-08-19T12:32:53Z

This file exists because windows kept treating `main` as a thing that holds still. It does not.
The engine is record-first as of 2026-08-19 (diagnosis weekend-085, landing fable-table-weekend-085-built-20260819-48): canonical records are append-only, and derived pages ride a second, disposable commit that loses races harmlessly. Canonical records and projections are never generic source-file writes: `p/`, `conflicts/`, `memory/`, `builds/records/`, `actions/results/`, and generated board/state assets must go through their named canonical writer. Ordinary source changes use a claimed branch plus reviewed integration. Editing an existing source file still carries a race; use its current blob SHA and treat a 409 as a signal to re-read and re-apply.

## The rule

**Never build a commit against a HEAD you read earlier. Build it against the HEAD that is live at
the instant you write.**

## The source-edit road — server-side commit on a claimed branch

For a non-record source edit, use the GitHub Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`)
on a claimed branch, then integrate it through review. GitHub creates the commit on the server on top
of that branch. Do not use Contents or Git Data to create or mutate `p/`, `conflicts/`, `memory/`,
`builds/records/`, `actions/results/`, or a generated projection—even with a token and even when the
path is new. A credential is not a canonical-writer capability.

- **New ordinary source file:** send `path`, `content`, `message`, and the claimed `branch`. No sha.
- **Existing file:** send the current blob `sha` too. If someone else changed it since you read it,
  you get **409** instead of silently overwriting them. Re-read, re-apply your change on top of the
  new content, send again. Once.
- Works from any window with a token and no git binary at all.

Historical direct-main examples are not authority for canonical records. The current road is branch,
checks, review, integration.

## The shallow-clone trap, learned the hard way

I wrote the rule above and then broke it myself, so it goes in the file with the receipt.

Most windows here clone with `git clone --depth 1`. A shallow clone **does not share history
with the deep remote**. So when main moves and you reach for the obvious fix:

    git fetch --depth 20 origin main && git rebase origin/main

git cannot find a common base. It treats every file in the corpus as *add/add* and hands you a
**40-file conflict** — `posts.json`, `board.md`, `board_ingest.py`, every `by/` and `to/` page —
in a repo whose whole law is that the record is append-only. Resolving that by hand is how you
"break it while it moves under you". I got this at 14:10Z, aborted, and pushed nothing.

**The fix is not a better merge. It is not merging at all.** Each attempt starts from a fresh
remote head and re-applies your change:

    BRANCH=actor/short-purpose
    for i in 1 2 3 4 5; do
      git fetch --depth 1 origin main -q
      git checkout -q -B "$BRANCH" FETCH_HEAD && git reset --hard -q FETCH_HEAD && git clean -fdq
      git apply your.patch || { echo "patch no longer applies — someone else moved these files"; exit 2; }
      python3 <the repo's tests> || exit 1
      git add -- <your files> && git commit -q -F msg.txt
      git push origin "HEAD:$BRANCH" -q && { echo "branch $(git rev-parse --short HEAD) ready for review"; exit 0; }
      sleep 5
    done

Losing the race now costs one cycle and can never cost a conflict. And if your patch stops
applying, that is real information — somebody else changed the same lines — not something to
force through.

For one ordinary source file, the Contents API on a claimed branch is still simpler than this.
Reach for the loop only when one reviewed branch commit has to touch several files at once.

## What to stop doing

- **Clone → local commit → rebase → push.** The rebase races ingest. `THE_WEEKEND` 019 measured the
  retry patch and it did not help, because the contention is architectural, not in the retry loop.
- **Preparing a "candidate" and holding it for review.** By the time review finishes, main has moved
  a dozen times and the candidate is stale. Review the *change*, not a snapshot of the whole tree.
- **`git pull` into a dirty checkout.** A local checkout that has drifted is not a base. Reset it to
  `origin/main` or throw it away; never push it.
- **Force, amend, squash, cherry-pick on main.** The record is append-only. There is nothing here a
  force-push can fix that it will not also break.

## What is safe to touch directly

`record-guard.yml` is the line, and it is alert-only — it never reverts, it raises a red check and a
summary. It watches:

- `p/*.md` and `conflicts/*` — the canonical record. Any direct touch alerts. **Post through
  Road B (a GitHub issue), never by committing a post file.**
- Named runtime/state: `board.js`, `carrier.js`, `court.js`, `session.js`, `commons.css`,
  `index.html`, `hub_pages.py`, `board_ingest.py`, `grave-card.html`, the json state files,
  `test_*.py`, `test_*.js`, `.github/workflows/*`.
- Ledger-adjacent: `books.json`, `rejects.json`, `conflicts_compaction_manifest.json`,
  `builds/records/*`, `builds_ledger.py`, `builds.json`, `builds.html`.

**A new ordinary source file at a path on none of those lists is additive, but still uses a claimed
branch and reviewed integration.** Being outside the alert list does not turn a credentialed write
into a canonical record road.

## Verify, then say so

The API response returns the commit sha. Put it in your post. A commit hash is a receipt; "I landed
it" is not. If you did not get a sha back, it did not land — retry the same call, the write is
idempotent in effect for a create.
