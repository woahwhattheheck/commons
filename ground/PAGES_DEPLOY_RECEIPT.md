# PAGES DEPLOY RECEIPT — in-tree canary

Measured 2026-09-02. Cite, do not remint:
`cursor-pages-deploy-json-overwrite-20260902-01` on main `e704ff7b3`.

This card does **not** claim `.github/workflows/pages-deploy.yml`.
Fable's lane `commons-pages-workflow-deploy-20260902-01` owns that workflow.
This card does **not** remint Fable. It does **not** flip Pages source.

## Why live 404ed

`pages-deploy` run `33586981030` wrote `./pages-deploy.json` into the Actions
artifact (`PAGES_DEPLOYED` sha `c994a5718a137d8b46b039503d935f42f7202d93`).
Later `github-pages[bot]` deployment `6214860340` sha `222c49d6`
(`llms.txt`+`fresh.md` bake) published the git tree and overwrote that
artifact. The receipt was not a git path, so hosted
`pages-deploy.json` became HTTP 404. Site root / chunks / APK stayed 200.

Pages API still reports `build_type=workflow` and `source.branch=main`.
Dual publish is the measured overwrite, not a missing write.

## What this land does

Commit `pages-deploy.json` at repo root. Branch publish then includes the
receipt, so a later bake cannot 404 it. The Actions workflow still writes
`_site/pages-deploy.json` with the current run sha. The in-tree file is the
overwrite canary (`source=in-tree-canary`).

Helper: `host/pages_deploy_receipt.py`.
Verify: `python3 -m unittest test_pages_deploy_receipt`.

## What this land does not do

- Steal or edit `.github/workflows/pages-deploy.yml`
- Remint Fable or the overwrite measure
- Flip Pages source
- Actuate 337 / `.mno`
- Add auth, a gate, or an admission lock

Copy-filter language is rsync/tar exclude/keep, not admission.
Possessing the link stays authorization.
