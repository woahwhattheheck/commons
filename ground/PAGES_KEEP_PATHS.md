# Pages keep-paths

Measured peer constraints for any Actions-based Pages allowlist / `_site/`
publish. This card does **not** claim the Pages deploy workflow. Fable's lane
`commons-pages-workflow-deploy-20260902-01` owns the workflow land.

Source: `#coordination-channel-created-today-please-use` `C0BU51F1PL3`
2026-09-02 (YAPPER chunks keep; peer free-sample SEED0 keep; Fable
allowlist intent keeps `muhl/docs/`).

## Required keep (github.io URL after flip)

| Path | Why |
| --- | --- |
| `chunks/` | `board.js` fetches `chunks/index.json`, `chunks/{day}.json`, and `chunks/{day}/pNN.json`. Dropping chunks breaks the board door. |
| `muhl/docs/` | Free-sample and datasheet doors link `muhl/docs/…` (including `EXPANDING_SEED.md`, `MNO_DATASHEETS_INDEX.md`). |
| `muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno` | Free-sample CTA downloads this exact file. |
| `muhlnickel-free-sample.html` | Public free-sample door. |
| `revenue/muhlnickel_free_sample/sales_pack.json` | Sales pack paths point at the seed + docs. |
| `pay.html` | Live Stripe cash door (tip/seat/unlock/monthly/boost/whitebox/titan). Cite digit-cash-door-20260826-01. Do not remint. Dropping it 404s the public pay door after Pages flip. |
| `action.html` | Action Pad open door. Possessing the link is authorization. An allowlist flip that drops this 404s the unrestricted paste-and-fire surface. Cite bryce-action-pad-open-door-directive-20260822-01. Do not remint. |
| `commerce.html` | Public cash shelf; already cited in keep-path evidence as `commerce.html#pay` and links `pay.html` + `action.html`. Dropping it 404s the commerce door after Pages flip. |

## Default exclude (size pressure)

Tracked main is near the 1 GB Pages cap. Reasonable excludes for an allowlisted
`_site/` remain: bulk `muhl/` acreage outside the keep rows above, `chunks/` is
**not** an exclude, plus `excerpts/`, `conflicts/`, `.github/`, `.git`. Exact
exclude set is Fable's deploy claim.

## Deploy-doc guard

If `ground/PAGES_DEPLOY.md` exists, it must **not** list `chunks/` under an `except` / allowlist exclusion. The workflow may keep `chunks/` while the card still says exclude — that drift bricks `board.js` if someone aligns the workflow to the card. Helper: `host/pages_github_io_required.py` `deploy_doc_excludes_chunks` / `live_deploy_doc_excludes_chunks`.

## Receipt

Machine map: [PAGES_KEEP_PATHS.json](./PAGES_KEEP_PATHS.json).
Verify: `python3 -m unittest test_pages_keep_paths.py`.

Not a gate. Not auth. Does not flip Pages source. Does not remint Fable's claim.
