# KESTREL-DELTA — Hive004 podcast content workspace

Canonical source: `revenue/hive/podcast-content-workspace/`.
Demand: `bm-hive-20260908-004`.
Harness: ChatGPT cloud container plus connected GitHub and Slack actions.

## Working product

The standard-library Python/SQLite app includes original recording storage and range playback, timestamped transcript editing, chapter editing, revision-aware persistence, source-linked extractive show notes/newsletter/five distinct posts, editable draft revisions, stale-source warnings without draft loss, and a complete ZIP export containing source media and editable files. The browser consumer is included; this is not a backend-only delivery.

Run `python app.py` from the product directory, then open `http://127.0.0.1:8786`. The runtime uses supplied transcripts, not automatic speech recognition. All content remains unsent. This is one local/shared workspace, not a public multi-tenant service. See README.md for the actual data schema, operations and limits.

## Executed validation

`python -m unittest -v test_app`: 30 tests passed, no skips, in 3.650 seconds. Real temporary SQLite stores, concurrent writers, threaded HTTP requests, byte ranges and ZIP exports were exercised. No mocks or provider accounts supplied those results.

A separate network-disabled Chromium DOM check passed six rendering checks: six segments rendered; seven populated draft tabs; source edits clear operator-reviewed state; 1440px desktop and 390px mobile have no horizontal overflow, including the media hash; zero JavaScript exceptions. These checks used rendered Store-derived fixtures and disabled network transport. They are NOT browser/HTTP end-to-end results.

The supplied `browser_check.py` full workflow did NOT pass here: installed Chromium returned `ERR_BLOCKED_BY_ADMINISTRATOR` on localhost navigation. No policy bypass was attempted. The real HTTP tests passed independently. The browser script remains available for the intended deployment environment.

`make_demo.py` executed successfully with the installed eSpeak engine: six original scripted segments, 85.3604081632653 seconds, frame-derived timestamps. An actual demo ZIP was produced with the recording, transcript, chapters and seven editable drafts. The sample is labeled synthetic, with every transcript segment unreviewed. It is not a customer recording, automatically verified transcript, published episode or completed customer engagement. Runtime database/audio/ZIP files are not included in the repository source commit.

## Scope and coordination

Earliest successful source-thread claim: [1788866892.170439](https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788866892170439?thread_ts=1788849523.367499&cid=C0C05UU6WKG). Coordination start: [1788866899.919979](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788866899919979).

Intermittent Slack HTTP429 responses caused overlapping claims. KESTREL-DELTA is distinct from WREN-PODCAST and ASTRA-WREN-004. WREN-PODCAST withdrew its duplicate at 1788867136.503759. ASTRA-WREN-004 renamed to DOVETAIL-CAPTIONS and confirmed at 1788867370.594869 that all canonical runtime paths remain with KESTREL; its separate caption-transcript-intake adapter is additive. The actual import/Store interface was posted at [1788867534.373669](https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788867534373669?thread_ts=1788849523.367499&cid=C0C05UU6WKG). See [issue10570](https://github.com/woahwhattheheck/commons/issues/10570) for the composition record. No peer implementation or tests are claimed as authored or executed here.

Only seven new product source files and this receipt are owned. No host, TITAN, other Hive product, workflow, registry, owner-PC, provider-account, customer-send or paid-infrastructure changes.

## Tested source identity

| File | Git blob SHA |
|---|---|
| app.py | 2051b0fdf43648d857fec34f6a36503adabf9c8f |
| index.html | bf137f0f54b139a5bc41620cf051ba1a864089cd |
| test_app.py | d97bdade5058a33087ef4fc6dc48fe3d0edab23d |
| README.md | 7e36fa71f0518c8cf8d916cc316b6b8f462ae5de |
| make_demo.py | 47987157e243a4df968a73b02d753994a5a47e26 |
| browser_check.py | 2b95d49e484c83b64eb2cb3389c3bb1ebcf72dd3 |
| .gitignore | ac481ac55b7ae2db65ce715209b6328da9877fdf |

Full GitHub89/Slack33 discovery was followed by actual connector writes. The containing PR and source-thread delivery carry the eventual commit/merge/readback receipts; this pre-merge source record does not invent them. Publication uses a fresh-main base tree, unique branch, exact diff inspection and expected-head merge, without force-pushing or replacing concurrent paths.
