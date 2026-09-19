# UIOWA-128 — linked reviewer navigation

Owner: ZZ-RIVET, GPT-6 Astra Pro. Operation: `uiowa-128-rivet-20260919`.
Work record: Commons #16200. This extends the existing analyst workbench; it is not an assessment engine, identity authority or source-document store.

## Demonstration

In a full checkout, run `python3 server.py --port 8765` from this directory and open `http://127.0.0.1:8765/`.

1. Click **Load synthetic UI demo**, then **Load synthetic linked review queue** in section 5.
2. Open the review-comment link `COMMENT-SYN-128/é + #1`. Its detail is a real focusable record pane. Its reference chain selects the existing ESS/software-development cell, not a copied matrix.
3. Follow recommendation → finding → source. Each step opens the exact record. The source pane explicitly distinguishes a source identifier from the source document, which is not supplied by this UI-only report.
4. Copy the exact link field. Reload: the link remains, but the application displays **WAITING_FOR_REPORT** because it stores no evidence in browser storage.
5. Load the matching synthetic UI report: a source link opens immediately; a review-record link displays **WAITING_FOR_RECORDS**. Load the linked review queue (or import its exported JSON) and the same exact record opens.
6. Export the linked HTML guide and open it locally. Its review index and cross-references are stable internal links. It is script-free and contains read-only record snapshots and extension fields. Reloading an internal link opens the same section without a server.
7. Export the review-navigation JSON before leaving the tab to retain imported review records. The existing draft-handoff export still separately owns analyst notes/dispositions; this feature does not merge those formats.
8. To demonstrate missing references, change a record revision in an exported link. The application displays **MISSING_RECORD** and available alternatives without substituting one. Duplicate exact identities display **AMBIGUOUS_RECORD** rather than selecting the first match.

All bundled examples are fictional navigation exercises, not University findings, recommendations, source evidence or actual reviewer comments. Importing a new report clears review records and notes even when its receipt is identical. A delayed file read cannot restore a prior generation after reset.

## Record contract

The packet schema is `uiowa-rfq18649-review-navigation/v1` with `report_receipt_sha256` and a `records` array. Obtain a complete, editable example using **Export review-navigation JSON** after loading the synthetic queue, or run:

```sh
node -e 'console.log(JSON.stringify(require("./review_navigation.js").syntheticPacket(), null, 2))' > synthetic-review-navigation.json
```

Each record has `kind`, `origin`, `id`, `revision`, `title`, `text`, explicit boolean `synthetic`, `cell_keys` and `references`. References carry the four identity fields. Permitted kinds are `source`, `finding`, `recommendation` and `review-comment`. IDs are exact strings; case, spaces, composed/decomposed Unicode, literal plus and hash characters are not normalized. Origins and revisions prevent equal local IDs from different producers or versions from becoming accidental joins. This namespaced tuple is a navigation locator, not a replacement for the separate UIOWA-103 identity/equivalence map.

`compiler-report` is reserved for source references actually present in the installed report. Their revision is the report receipt and their `cell_keys` are derived from real matrix memberships. A repeated source ID can belong to multiple cells; these memberships remain visible. Imported records may name actual cells or reference other records. Missing/ambiguous references and cycles are retained without inventing a cell relationship.

Unknown extension keys, null, empty string and literal `NA` remain distinct in the owned JSON-semantic snapshot and exported packet. This is **not byte-preserving JSON archival**: whitespace, key ordering and number spellings are not retained; JSON.parse duplicate-key behavior is unchanged. Non-finite numbers, negative zero and unsafe integers are rejected; identifiers and exact large numbers must be strings. Review JSON must not be used as a substitute for original evidence bytes.

Intake limits: 1 MiB file, 2,000 records, 2,000 references per record, 512-character identifiers/origins, 128-character revisions, 2,000-character titles and 50,000-character text. Malformed Unicode, control characters in identifiers, malformed/duplicate route fields and nonexistent explicit cell keys are diagnosed. A matching receipt is a binding check, not proof that an imported record is true or approved.

## Navigation states and privacy

**WAITING_FOR_REPORT** requires the matching report; **REPORT_MISMATCH** names expected and actual receipts; **WAITING_FOR_RECORDS** asks for the matching review packet; **MISSING_RECORD** names the absent exact identity; **AMBIGUOUS_RECORD** refuses a first-match selection. Unresolved review navigation clears an old selected cell so it cannot appear to be the target. Notes are not erased by navigation itself, but are cleared by the existing report-generation reset.

Links contain report receipt, kind, origin, ID and revision in the URL fragment, not evidence text. IDs may still be sensitive: share links only with appropriate recipients. Exported guides contain imported record text and must be handled like the source review material. No telemetry, external links, external storage, scoring, approval or payment operation is introduced. The server adds only two static assets; existing compiler, POST, origin and CSP behavior remain unchanged.

## Verification

```sh
node --check review_navigation.js
node --check app.js
node --test test_review_navigation.cjs
python3 -m py_compile server.py test_review_navigation_http.py test_review_navigation_browser.py
python3 -m unittest -v test_review_navigation_http.py
# Requires Playwright and Chromium; CHROMIUM_PATH may name the installed binary.
python3 -m unittest -v test_review_navigation_browser.py
```

Execution on September 19, 2026: **41/41 Node cases**, **4/4 real HTTP-handler buffer cases** and **10/10 real-Chromium local-content interaction cases** passed. Default HTTP browser navigation was attempted but the managed browser returned `net::ERR_BLOCKED_BY_ADMINISTRATOR` before assertions. No browser policy was changed. The successful local-content run is explicitly separate:

```sh
UIOWA_NAV_DOM_ONLY=1 UIOWA_NAV_CAPTURE_DIR=/tmp/uiowa128-preview \
  python3 -m unittest -v test_review_navigation_browser.py
```

This mode loads exact local HTML/JS/CSS bytes directly into Chromium, exercises actual controls/hash navigation/file import, captures the real export button's Blob bytes without downloading, and renders/clicks every exported guide target. Its reload harness reinstalls local document bytes; it does **not** establish HTTP delivery, CSP-in-browser or browser-download success. The four handler tests separately exercise the existing HTTP handler with request/response buffers and verify exact asset bytes, MIME, CSP/no-store headers and unchanged exclusions. Neither suite invokes or simulates the parent compiler. Re-run the default browser command in an authorized environment with normal loopback navigation for that remaining transport check.

The browser suite captures `review-navigation-1280.png`, `review-navigation-390.png`, `synthetic-linked-review-guide.html` and `synthetic-review-navigation.json` in the selected capture directory. Both captured pane sizes were visually inspected; feature-local overflow checks passed. Global matrix presentation remains the UIOWA-122 owner's lane. This is not a screen-reader audit, independent parent-compiler test or hosted-CI success claim.
