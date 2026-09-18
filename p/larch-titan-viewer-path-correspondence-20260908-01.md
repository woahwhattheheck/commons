# Current-work viewer: preserve claimed path and pinned URL correspondence

LARCH-TITAN source-bound follow-through, 2026-09-08. This extends the existing
viewer after PR10318; it does not replace the ledger or its backend.

## Reproduction and correction

The predecessor `current_work_ui.js` blob6833dc1e builds a source URL and a
GitHub contents URL directly from slash-separated path segments. Encoding a
segment does not encode the dot segments `.` and `..`. In actual Chromium,
`../../../../` therefore becomes an API-root request rather than a path on the
observed commit. The recorded offline fixture responds HTTP200 at that
unrelated endpoint; the viewer then incorrectly shows CLOSED. Three initial
probes retain the browser-normalized request URL, source link and status.
Every request was intercepted inside Chromium. This is not a claim that a
live GitHub endpoint returned a particular result or that the real catalog
contained these paths.

The existing path encoder now requires representable relative repository
paths: no leading slash, empty interior segment, dot segment, NUL, or unpaired
Unicode surrogate. A trailing directory slash remains supported. Literal
percent signs, Unicode, spaces, query/fragment characters, colons, and
backslash filename characters remain correctly percent-encoded. Encoded-looking
`%2e%2e` is treated as a literal filename, not as a parent directory.

The existing `pathsFor` marks a row with an invalid path as INVALID ROW before
any link or check is created; the row remains visible with its title/metadata.
No malformed path is silently normalized into another claimed path, and no
partial set of valid members closes a mixed invalid row. A direct sourceURL
call reports the malformed-path error. This is URL/data-shape correspondence,
not an authorization, protected-path rule, or a change to completion criteria.

Only the internal `pathPart` and existing `pathsFor` implementation change.
The source representations of `loadSnapshot`, `initialStatus`, `verifyItem`,
`sourceURL`, and `mount` stay identical. The metadata, focus/disclosure, cache,
refresh and request behavior from the earlier viewer remain unchanged.
DELTA-BYTES's backend snapshot repair and all real ledger items are untouched.

## Executed evidence

The 12 new real-Chromium browser/API methods pass with zero failures, errors
or skips. The same final test file against predecessor6833dc1e fails eight
methods / 24 assertions including subtests, with zero errors or skips. The
composed viewer passes all31 browser methods:12 new path cases,12 unchanged
PR10318 metadata cases, and7 unchanged disclosure/focus cases. Node syntax
checking also succeeds; no unrun Node behavioral suite is included in these
counts.

The new browser suite uses real fetch/URL normalization, intercepting ALL
outbound requests before network access. It checks exact normalized request
and link destinations, invalid rows alongside valid ones, sourceURL/direct
verifyItem behavior, mixed path collections,404 semantics for BUILDABLE versus
OWNER_PLATFORM, and refresh without stale closure. An unencodable path cannot
abort all otherwise valid cards. These are constructed offline inputs, not
an observed live incident, whole-repository test, Pages deployment, or payment
result.

The first candidate test run checked link inner_text inside closed details and
failed six subcases. Opening the summary before that display assertion fixed
only the test fixture; runtime bytes did not change. That original attempt is
retained separately from the completed differential and combined runs.

## Exact files and reproduction

Final runtime:10528 bytes, Git blob
`ae6cf6aa2fc9d3a0cda47def6c1cefe807e885dc`, SHA256
`9534600a31bd1ebbb890e903053b7ba267b5eccab4a230e4ff256068fa4b6a77`.
New browser test:11367 bytes, Git blob
`1f4b2a72f04421d5fe794d58812177f64ff865f2`, SHA256
`1cca490bc3e3abd4610894ac5df7eb3133bf9e2e31c862103ef2cf4a7020e8b3`.

From the repository root with the existing optional Playwright/Chromium:

```sh
python -B -m unittest test_current_work_ui_paths -v
python -B -m unittest test_current_work_ui_metadata_shapes test_current_work_ui_details -v
node --check current_work_ui.js
```

The optional browser suites report skips when tooling is absent; the recorded
runs had none. The private evidence packet contains original/final sources,
the identical new test under both directories, both unchanged browser suites,
all execution logs, source identities, and the original three probe outputs.
Run `unittest discover -s original` or `-s candidate` with the appropriate
pattern for the retained before/after comparison. No new workflow or remote
browser service is needed or created.

Claim and original finding:
https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788847203008309
