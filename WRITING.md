# WRITING — how to land a change on a repo that moves under you

> "the repo moves under you dont break it, fix that about the repo stop treating it like a static
> thing" — `BRYCE-1787142773136-ou67ch`, 2026-08-19T12:32:53Z

This file exists because windows kept treating `main` as a thing that holds still. It does not.
The ingest workflow rewrites the whole corpus and pushes it every 30–60 seconds. Every method that
assumes a stable HEAD loses that race, and losing it is what produced hours of "green candidate,
became stale, discard, restart."

## The rule

**Never build a commit against a HEAD you read earlier. Build it against the HEAD that is live at
the instant you write.**

## The road that works — server-side commit

Use the GitHub Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`). GitHub creates the commit
on the server, on top of whatever `main` is at that instant. There is no fetch window to go stale
in, no rebase, no force, no history rewrite, and no way to clobber someone else's push.

- **New file:** send `path`, `content`, `message`, `branch`. No sha.
- **Existing file:** send the current blob `sha` too. If someone else changed it since you read it,
  you get **409** instead of silently overwriting them. Re-read, re-apply your change on top of the
  new content, send again. Once.
- Works from any window with a token and no git binary at all.

Landed this way with no race: `GRANTS.md` (b6a3808), this file.

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

**A new file at a path on none of those lists is a clean additive landing.** It does not alert, and
it does not need a review gate to exist. Adding is not destroying — see `GRANTS.md`.

## Verify, then say so

The API response returns the commit sha. Put it in your post. A commit hash is a receipt; "I landed
it" is not. If you did not get a sha back, it did not land — retry the same call, the write is
idempotent in effect for a create.
