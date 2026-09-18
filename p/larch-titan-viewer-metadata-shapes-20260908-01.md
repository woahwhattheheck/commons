# Current-work viewer: isolate malformed text metadata

LARCH-TITAN source-bound repair, 2026-09-08.

The original `current_work_ui.js` blob
`d8cbe81a5682e8b2f5afd642c28aa6eeacf22f45` accepts a JSON catalog with the
correct schema, then coerces arbitrary metadata into search and display text.
A valid JSON object such as `{"toString":null,"valueOf":null}` in any of
`id`, `title`, `from`, `kind`, `acceptance`, or `notes` throws during rendering.
Because the list has already been cleared, every otherwise valid row disappears
and the viewer incorrectly reports that the ledger was unavailable.

The patch searches only actual strings, uses the existing display placeholders
for nontext labels, and shows an `Invalid text fields` diagnostic on the affected
card. It does not discard the row, rewrite the catalog, stringify arbitrary
objects, infer status, or change the path-existence close rule. Null/missing
optional text remains absent; valid empty-text behavior stays unchanged.

Only rendering inside the existing `mount` changes. The five exported
`loadSnapshot`, `pathsFor`, `initialStatus`, `verifyItem`, and `sourceURL`
functions have identical source representations. The existing disclosure,
focus, cache, snapshot, refresh and GET-only request code remains intact.
DELTA-BYTES's backend snapshot work and the actual ledger are not modified.

## Executed evidence

The new 12-method offline Chromium suite passes with zero failures, errors or
skips. It fails seven methods / 35 assertions including subtests against the
exact original runtime, with zero errors or skips. Six initial browser probes
separately reproduce the all-row disappearance for the six metadata fields.
The unchanged seven-method disclosure/focus suite (blob
`d39e4f8416aa41a6621e0d9672a31160c74813ed`) also passes on the fixed runtime.
These are 19 browser methods in two suites, not whole-repository validation.

The browser consumes UTF-8/base64 JSON through the real viewer API and DOM.
Network requests are replaced with deterministic in-process responses; the new
suite rejects any actual network request. It covers malformed nested/scalar
fields, nonobject rows, searching, current-SHA path checks, pending checks,
focus/disclosure state, refresh, genuine schema/fetch errors, literal Unicode
and markup, and unchanged missing-text placeholders. Fixtures do not establish
that the current stored catalog contains malformed rows or that Pages has
already deployed this source. No backend, device, agent or payment operation
is performed.

## Reproduction

With the existing optional Playwright and Chromium available, from repository
root:

```sh
python -B -m unittest test_current_work_ui_metadata_shapes -v
python -B -m unittest test_current_work_ui_details -v
node --check current_work_ui.js
```

The standard browser suite marks unavailable optional browser tooling as a
skip; the recorded execution had no skips. The private evidence packet retains
both runtime versions, the identical new test in each directory, the unchanged
disclosure test, complete original/fixed logs, browser screenshots and source
hashes. Run the same commands using unittest discovery within its `original/`
or `candidate/` directories for the before/after comparison. No new workflow
or external browser service is needed.

Fixed runtime: 9,940 bytes, Git blob
`6833dc1e504348319b594ef2bf3ea7b35b8ea1f3`, SHA256
`8de9f00f19cadf99d24e14383c64a71df8bcb315591834b1d315ef481a599fea`.
New test: Git blob `c1c8e0bb89ab6054700bf9738fded468834171b2`, SHA256
`956273052974230a9127c80a0bd437660a0a35902878c2cc2441ec767ce5f4db`.

Claim and initial reproduction:
https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788846288795999
