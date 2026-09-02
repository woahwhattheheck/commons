# PAGES DEPLOY — the Pages URL now carries a SHA receipt

Measured 2026-09-01/02 from current main. Owner approval: Bryce, in-session
2026-09-01 ("yes to all") after the measured Pages pressure was raised.
Claim: `commons-pages-workflow-deploy-20260902-01` (Slack #delegations).

Doc keep-align assist: `digit-pages-deploy-doc-keep-align-20260902-01`
(does not remint Fable's claim). Allowlist prose now matches the workflow and
[PAGES_KEEP_PATHS.md](./PAGES_KEEP_PATHS.md): `chunks/` stays.

## Why

- Tracked blobs on main: **880.9 MB** against GitHub's **1 GB** Pages cap.
  `muhl/` = 597.7 MB (`.mno` 474 MB). `p/` = 20,982 files in one directory.
- The legacy branch-build Pages source publishes the whole tree except
  `.git`/`.github`, and every push cancels the build in flight. The 08-25
  census counted 23 of 30 runs cancelled; the same pattern held tonight.
- [HEAD.md](./HEAD.md) and [COMMONS_ARCHITECTURE_300FT.md](./COMMONS_ARCHITECTURE_300FT.md)
  both say Pages needs an explicit publish receipt tied to an immutable Git
  SHA. Git convergence never proved Pages deployment.

## What changed

`.github/workflows/pages-deploy.yml` builds `_site/` from the exact main SHA
and publishes it through `actions/deploy-pages`. Repo Pages source is
`GitHub Actions`, not the branch build.

Allowlist: the whole tree **except** bulk `muhl/` (keep `muhl/docs/` and
`muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno`), `excerpts/`, `conflicts/`,
`.github/`. **`chunks/` MUST stay** — `board.js` fetches `chunks/index.json`,
`chunks/{day}.json`, and `chunks/{day}/pNN.json`. `pay.html` stays (cash
door; not on the except list). Roughly 235 MB of bulk `muhl/` drops; board,
free-sample, and pay doors remain.

Receipt: every deploy writes `pages-deploy.json` at the site root with the
built SHA, run id, attempt, keeps, and the exclusion list, and prints
`PAGES_DEPLOYED url= sha= run=` in the job log and summary. That run is the
`PAGES_DEPLOYED` state in the truth ladder. Read it, do not infer it.

Concurrency is non-cancelling: one run active, one queued, so pushes
coalesce. A `*/10` schedule converges any missed push event.

## What did not change

- Git, raw.githubusercontent, the contents API, ntfy, Slack, issues, the
  Action Pad, MCP, and every posting road. `.mno` files are exactly where
  they were. HTTP is not the computer.
- No auth, no gate, no identity, no admission. Possessing the link is still
  authorization.

## Measure

```bash
curl -s https://woahwhattheheck.github.io/commons/pages-deploy.json
git ls-remote https://github.com/woahwhattheheck/commons.git HEAD
gh run list -R woahwhattheheck/commons --workflow pages-deploy.yml --limit 5
python3 -m unittest test_pages_github_io_required test_pages_keep_paths
```

If `pages-deploy.json` lags `HEAD`, the queued run has not landed yet; that
is `PENDING`, not stale truth. If more of `muhl/` (beyond docs + SEED0) or
`excerpts/` / `conflicts/` is needed on the Pages URL, add it to the
allowlist in the workflow on a branch and merge; do not revert to the legacy
branch build. Do not put `chunks/` back on the except list.
