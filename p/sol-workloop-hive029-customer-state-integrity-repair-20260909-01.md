# HIVE029 customer-state integrity repair

Operation: `HIVE029-CUSTOMER-STATE-INTEGRITY-REPAIR-20260909-01`
Demand: `bm-hive-20260908-029`
Consumes: post-merge independent review `5161351475` on PR `#11937`
Slack claim: `C0C09QN8MQR / 1789000328.037319`
Scope correction: `C0C09QN8MQR / 1789000494.794559`

## Scope

Only:
- modified `revenue/hive_prospect_workspace/index.html`
- new `revenue/hive_prospect_workspace/integrity.js`
- new `revenue/hive_prospect_workspace/test_integrity.cjs`
- this new receipt

The landed `app.js`, `test_app.cjs`, `model.js`, ASTER-LINK SQLite backend/panel, provider/customer state, outreach, billing, and deployment are not changed.

## Bounded repair

`integrity.js` is loaded immediately after the landed `app.js` and before `DOMContentLoaded`. It composes with the existing exported Fieldnote API rather than reconstructing the owner's controller.

1. Browser storage absence is now exactly `localStorage.getItem(...) === null`. Present empty-string or otherwise invalid saved bytes fail validation, stay byte-untouched, and keep ordinary writes blocked until explicit validated restore/reset.
2. Every import preview is bound to the controller state revision that produced it. Successful commit, merge, update, saved-segment mutation, restore, or reset advances the revision; a preview from an older revision fails closed instead of replacing newer live state.
3. Applying a saved segment keeps the saved filter object authoritative for query/export even if an industry/tag/stage value has disappeared from the current option inventory. Missing saved values are rendered as explicit no-current-match options rather than silently becoming blank/ALL.
4. Filter/segment transitions clear currently visible selections before they can become hidden, and the merge boundary independently intersects requested IDs with the current visible query. Fewer than two visible IDs fail closed.

The existing model remains authoritative for identity/merge semantics, safe source URLs, spreadsheet-safe CSV encoding, and state validation. The shim adds no `fetch`, XHR, WebSocket, beacon, provider, messaging, payment, or other network-send path.

## Frozen preimages and candidate blobs

Composition base main: `9b3e3f441ea890478cc2b97ead91703a2ba6189d`
Base tree: `02545a39c8f29db6b57cfb3c6fd4fb3615d075e7`
Index preimage: `35bde897010685cccae17cba028c550a2dc1a21d`
Integrity/test/receipt preimages: absent (404)
Candidate index blob: `e47d79381817e56a55aaf046f6bcc7d69689c008`
Candidate integrity blob: `616039fcb24f56d4d9a170cba2a229464e3016af`
Candidate test blob: `0a5303f8ee5fdc8fe93d8caa654ee027721c1431`

## Validation

The exact integrity and test candidate blobs were reproduced locally by Git object hash before publication. `node --check` passes both files. `node --test test_integrity.cjs` passes 7/7 against declared storage/controller/DOM boundary adapters, covering empty-string corruption, stale preview rejection with preserved intervening state, exact saved-segment filters, visible-only merge, selection clearing, script order, and no network primitive. The local HTML used for the script-order unit was a minimal shell; therefore this receipt does not claim that unit exercised the full checked-in HTML. GitHub compare/PR inspection separately constrains the real index change to the single integrity-script include.

No native-browser acceptance, provider integration, customer result, deployment, billing, or generic-repository CI PASS is claimed unless separately evidenced after publication.
