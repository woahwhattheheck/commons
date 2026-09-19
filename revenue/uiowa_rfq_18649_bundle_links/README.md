# UIOWA-119 — portable bundle citation checks

An offline, non-mutating verifier for local files and explicit locators in an
exported review bundle. It complements the UIOWA-093 record-ID traceability
rehearsal: that component checks relationships between records; this component
checks the file and destination that a reviewer is given. No network service,
model, database, credential, scheduler, or package install is used by the core.

The example preserves two **actual published synthetic files** from UIOWA-093,
Commons PR #16157 at `6152c82071626faa95e119fbf2a35304bcf401e9`. Attribution:
Keystone. Their content, original path, Git blob identity and SHA-256 are pinned
in `source_snapshot.json` and rechecked by the example builder. They are not
University observations. Existing workbench/compiler/report files are unchanged.

## Run

From this directory, with Python 3.10 or newer:

```sh
python build_example.py /tmp/uiowa-119-example
python verify_bundle.py /tmp/uiowa-119-example /tmp/uiowa-119-example/citations.json
python -m unittest -v
python -O -m unittest -v
```

Choose a new output directory: the example builder never overwrites an existing
one. Open the generated `review.html` in the delivery environment. Its four
review questions lead to explicit HTML IDs, including a percent-encoded Unicode
filename. The guide, source renderings, original Markdown/CSV and `citations.json`
form one portable bundle. No files outside that generated directory are changed.

The checked example has **19 verified references**: eight CSV evidence-record
locators, three report locators, six guide links and two return links. See
`validation_receipt.json` for executed scope and the browser-runtime limitation.

## Manifest contract

Paths in `source` are bundle-root-relative. `target` is a URL-style path relative
to the citing source's directory, not relative to the manifest. A fragment-only
target refers to that same source. `source_line`, when supplied, is a positive
1-based line number in the citing text file. HTML scanning records actual link
line numbers. A manifest citation is an explicit assertion of where a reference
originates; it is not a claim that arbitrary prose has been exhaustively parsed.

```json
{"version":1,"scan_html":["review.html"],"citations":[
  {"id":"interview","source":"review.html","target":"sources/evidence.csv",
   "locator":{"kind":"csv","column":"evidence_id","value":"E-006"}}
]}
```

Supported destinations: existing regular files; exact HTML `id` / legacy anchor
`name`; conservative simple ATX Markdown headings and literal HTML anchors;
explicit 1-based line ranges; unique exact quotations; unique CSV column/value
records, including quoted multiline fields. An optional `sha256` binds the cited
bytes, independently of locator validity. All requested checks must succeed.
Repeated simple Markdown headings receive deterministic suffixes. Complex
Markdown inline formatting and renderer-specific slugs require explicit IDs;
setext headings are not guessed. PDF/Word page locators are **not implemented**.
Whole-file existence for a PDF does not claim the PDF is valid or readable.

## Diagnostics and coverage

JSON output retains citation ID, original source, original target, source line,
resolved path, status, explanation and suggestions. Missing/renamed destinations,
changed bytes, missing/duplicate anchors, ambiguous CSV keys, overlapping repeated
quotes, malformed input and case/Unicode filename collisions cannot silently pass.
Exact-content rename suggestions are available when the citation has `sha256`;
suggestions never rewrite a reference. Fix the actual bundle/manifest, then rerun.

External URLs are `EXTERNAL_UNCHECKED`; query-dependent local navigation and HTML
`base href` are unresolved. Out-of-bundle paths/symlinks are reported without
inspection. This is a bundle-scoping behavior, not a repository publication or
permission gate. Input text inspection is bounded to 4 MiB per file. Checks do
not establish source truth, maturity, confidence, factual findings, or the
availability of external websites. Unselected HTML files and arbitrary Markdown
link syntax are outside coverage. Empty coverage is not a passing report.

Exit code 0 means every selected reference verified. Exit 1 means unresolved
references or empty coverage. Exit 2 means an invalid top-level input or I/O error.
No HTML links are executed by the verifier.

## Optional browser rehearsal

`browser_smoke.py` is a separate development harness requiring Playwright and
an installed Chromium executable. It serves only the generated example on a
short-lived loopback server and blocks external browser requests. It checks the
four question links and destination persistence after reload. It installs no
service and stops the server when the command ends.

```sh
python browser_smoke.py /tmp/uiowa-119-example --browser /path/to/chromium
```

This cloud runtime blocked both file and loopback browser navigation with
`net::ERR_BLOCKED_BY_ADMINISTRATOR`. Therefore **browser click/reload verification
is not claimed**. The stdlib unit/integration tests, source-identity checks, and
19 destination checks did execute. Run the optional harness in the intended
review environment before claiming browser navigation coverage there.

## Ready-to-open checked example

`checked_example/review.html` is the generated bundle already checked by this
component, not a separate demo implementation. Copy the entire
`checked_example/` directory together to retain relative links. Its saved
`verification.json` is an actual deterministic 19-reference checker result;
it does not contain or imply browser click/reload evidence.

```sh
python verify_bundle.py checked_example checked_example/citations.json
python -m unittest -v test_checked_example
```

`test_checked_example.py` regenerates the bundle into a temporary directory and
compares every byte with the published example, then recomputes the saved report.
Tests never regenerate expected values in place. A sample edit, stale report or
missing destination is a regression until an operator deliberately rebuilds and
reviews the sample. `delivery_receipt.json` binds the ready-to-open files and
records this supplementary execution; the earlier core receipt remains historical.
