# SOL-TERN Conversation Desk standalone release receipt

- Demand: `bm-hive-20260908-005`, additive customer-delivery lane only.
- Original application: ASTRA-OSPREY-005, merged in PR #10587. This change does not edit application runtime/UI/schema/OCR/drafting/restore code.
- Slack claim receipt: `1788869640.244829` in `#hive-saas-builds`.
- Publication preflight main: `d54597728fa15442733c13a710cb4ff13875beb5`.
- Preflight tree: `edc68f5163a6137b1528c2e1d578b3342d3a28d6`.
- Exact runtime blobs consumed and unchanged at preflight: `app.py` `9343f224c66db9fbdfb8baf9745713da83be6e47`; `index.html` `0841077a114e18ec94f8272084c416e1af23b413`; `desk.js` `5930cf43300eb925e722e1f8e9f87cb34537821e`; `README.md` `4976b0697689a8035d6b7da31846db812e721715`.

## Authored additive files

SHA-256 before connector publication:

- `revenue/hive/conversation-desk/build_release.py` — `ea87d2dedd2902682e30770c60b4af4f8172697a3283df771644a4f5503964ef`, 6307 bytes.
- `revenue/hive/conversation-desk/test_release_package.py` — `f64be43a8693789dce98bc5e1f543f3868f04dd805c0252de0f103b454f7dbe3`, 12816 bytes.
- `revenue/hive/conversation-desk/RELEASE.md` — `42261711cbd040def6406a6c664110a689772d7a3be598711fc3ef0aa6cc2d88`, 2072 bytes.
- `.github/workflows/conversation-desk-release.yml` — `b28b5f0a7013bb96be413f82e8ad407e2c561a2549bdfbdc58044afbc27cac26`, 3088 bytes.

The release ZIP allowlists only `app.py`, `index.html`, `desk.js`, and `README.md`, then adds generated `START_HERE.md` and `manifest.json`. It never recursively sweeps the product directory. Runtime SQLite/WAL files, screenshots/images, JSON exports, logs, caches, secrets, test files, restore/import artifacts and arbitrary customer files are not distribution inputs.

## Executed before publication

- `python -m py_compile build_release.py test_release_package.py`: pass.
- `PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_release_package.ReleaseBuilderTests`: **14/14 pass**, 0 failures/errors, 1.666 s in the cloud work directory.

Those local methods validate deterministic ZIP bytes, exact allowlist/one root, manifest hashes, fixed metadata, non-recursive privacy exclusions, missing/directory/symlink/size rejection, existing/dangling/competing destination preservation, and real builder CLI repeat behavior. They use synthetic allowlisted file fixtures and are not claimed as the extracted application acceptance.

The new GitHub workflow separately runs `test_release_package` against the actual checked-out current application, the existing `test_app` suite, and `node --check desk.js`; only after those pass does it upload the standalone ZIP + build/source/hash receipts. Hosted results are to be recorded on the PR/main run, not backfilled here.

No deployment, customer contact, provider-account write, payment, spend, owner-PC work, automatic messaging, external model call, customer data or force-push is part of this lane.
