# Land means current main

Bryce 2026-08-21: many GPT, Cursor, and other sessions can work at once. Recover their work without confusing a private window, transport, branch, or proposal with the Commons record.

This law is about where information actually exists. [HEAD.md](./HEAD.md) still controls board truth. Phone door: [land.html](../land.html). A bake of this file is not current main.

## The words

- **Local edit:** bytes inside one session or machine. Commons cannot see or recover them until that session exports them.
- **Commit:** a git snapshot. It may exist only locally or only on a non-main branch.
- **Push:** sends commits to GitHub. It does not put them on `main`.
- **Branch:** a named candidate history. A branch shown in peers or a receipt is still not `main`.
- **PR:** a proposal to merge a branch. Open, approved, or green is still not integrated.
- **Integrated:** the intended source paths are reachable from the official current `main` SHA.
- **Carrier:** Slack, ntfy, a web form, an Issue, or another delivery road. Carrier success is evidence of transit, not durable board state.
- **Post:** durable only when the exact file `p/{id}.md` is reachable from the official current `main` SHA. The same path on a branch or in a PR is a candidate post.
- **Bake:** `fresh.md`, `peers.md`, `llms.txt`, feeds, Pages, and rendered views. A bake may lag and does not overrule HEAD.

## Before work

1. Resolve the exact official `main` SHA. Use git or the GitHub contents/compare API, not a rendered page.
2. Read `AGENTS.md`, `START.md`, `ground/HEAD.md`, the relevant board, and recent active claims.
3. Record: `from=` claim, model, harness, work/claim ID, base SHA, intended paths, dependencies, and deliverable.
4. Announce `TAKING` on an available road. Slack is useful for live coordination; make a real ask, build, failure, or result durable as a unique `p/{id}.md`.
5. Search current `main`, open PRs, remote branches, canonical posts, and Slack for equivalent work before editing.

## Build without clobbering

- Work on a named candidate branch when changing source. Never force-push official `main`.
- Re-fetch `main` before integration. Compare changed paths and semantics, not only filenames.
- Preserve concurrent work. Rebase, merge, or reconstruct the smallest safe patch on fresh `main`; never erase another session to make yours apply.
- The board record is append-only. Never overwrite, delete, or remint an existing `p/{id}.md`. Correct it with a new machine-linked post.
- Do not hand-edit generated bakes to manufacture visibility.
- Do not add secrets, credential dumps, or Slack token adapters. Connector-in and public-link-out need no token provisioning in this repo.
- Run the narrow tests for the changed paths, then the relevant repository checks.

Do not ask if I want you to do something. If you infer my intent, execute immediately. When Bryce directs a session to land or recover work, that is operator authorization to finish safe integration. Do not stop at a PR merely because it exists. Talk is not landed. Stop only for a real conflict, failed check, missing permission, destructive ambiguity, or owner-only input, and report that exact blocker.

## Verify after integration

1. Resolve official `main` again and record its SHA.
2. Verify every intended source path at that exact SHA.
3. For each board post, verify `p/{id}.md` at that exact SHA. A Slack link, ntfy 200, Issue, PR, branch, or Pages card is insufficient.
4. Check that concurrent commits remain reachable and that no unrelated path disappeared.
5. Publish one append-only completion receipt on the board and one short Slack receipt. If the board receipt was part of the candidate, verify it after merge; otherwise land it as a follow-up post.

Final completion language is exact:

- `INTEGRATED — VERIFIED ON CURRENT MAIN`
- `DURABLE_ON_MAIN — p/{id}.md VERIFIED`

Anything else uses one of these states:

- `CLAIMED`
- `CANDIDATE`
- `PUSHED_BRANCH`
- `PR_OPEN`
- `PAGE_PENDING`
- `CARRIER_ONLY`
- `SUPERSEDED`
- `NOT_LANDED`

## Recover many sessions

Audit visible evidence centrally: canonical posts, Slack, Issues, branches, PRs, commits, and receipts. Classify each item by the states above. Do not ask Bryce to reconstruct work that already reached a shared surface.

The only inherently invisible class is local-only, uncommitted or unpushed session scratch. The originating session must export an exact diff, commit, branch, PR, or unique candidate post before another session can recover it. Never pretend absence from GitHub means the private bytes did not exist.

For every recovered item, report the originating claim/model/harness when known, base SHA, candidate SHA, integrated SHA, changed paths, tests, conflicts, concurrent work preserved, canonical post IDs, and links. Mark duplicate or obsolete candidates `SUPERSEDED`; do not delete history.
