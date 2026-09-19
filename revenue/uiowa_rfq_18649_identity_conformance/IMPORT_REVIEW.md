# Reviewing an import without hiding changed references

**Synthetic demonstration only. No University findings, approval, assessment authority, or automatic joins.**

A summary can say "two unresolved references" both before and after an import while describing two different problems. This kit makes that change inspectable rather than declaring the import unchanged.

## The worked import

Four existing source, observation, finding and recommendation occurrences are joined by a second origin's source with the same local label and a previously missing service. All four existing occurrence IDs and original records remain unchanged. Two new occurrences are added; none are removed or re-keyed.

The explicitly qualified source reference retains its exact original target. The reference naming only `source / SRC-1` moves from one candidate to two and becomes ambiguous, with no selected target. The service reference moves from missing to resolved. The other missing source remains visible and unresolved.

**Unresolved totals: 2 before, 2 after. Actual changes: 1 newly unresolved and 1 newly resolved.** Equal totals are not evidence that the same references remain unresolved. In this controlled fictional fixture only records are added, so the observed transitions can be attributed to that addition. The general comparison tool does not infer a cause when other declarations also change.

## Reproduce against the actual canonical mapper

From the repository root, with Python 3.10 or newer and no third-party runtime dependencies:

```sh
python -m unittest discover -s revenue/uiowa_rfq_18649_identity_conformance/tests -v
python -O -m unittest discover -s revenue/uiowa_rfq_18649_identity_conformance/tests -v
python revenue/uiowa_rfq_18649_identity_conformance/demo_import.py --output-dir /tmp/uiowa-import-review
```

The output directory must not exist. The generator writes `snapshot-before.json`, `snapshot-after.json`, `import-impact.json`, `import-impact.html` and `manifest.json`, with the manifest last. It refuses existing directories and never recursively deletes a path. A failed write can leave an incomplete directory; this is not an atomic multi-file transaction.

Open `import-impact.html` in a browser. It is a static, script-free document with no external dependencies or network requests. At narrow widths, the unresolved-reference table scrolls within its labelled, keyboard-focusable region. The full comparison and both complete original snapshots are retained in its disclosure. There is no separate server, installation or access key.

The initial actual execution uses canonical commit `6176eb9e74f634c58036789296a71e88ee72d7` only as a historical description; the authoritative target identity is the exact Git blob below. Require the exact tested source bytes with:

```sh
python revenue/uiowa_rfq_18649_identity_conformance/demo_import.py --expect-blob ee97b82d7e198aad99beef961f09b0eee194be48 --output-dir /tmp/uiowa-import-pinned
```

`--mapper` accepts trusted local Python source and executes it. Review its origin before use. The optional blob pin is checked against the exact bytes before execution. Missing source or a pin mismatch is an error, not a skipped passing test. No canonical source is downloaded, vendored or replaced by this kit. New core revisions need a fresh execution receipt; the initial result does not certify later repairs.

## Inspect two existing reports

```sh
python revenue/uiowa_rfq_18649_identity_conformance/import_impact.py before.json after.json
python revenue/uiowa_rfq_18649_identity_conformance/import_impact.py before.json after.json --format html
```

Both commands write to standard output only and leave source reports unchanged. Exit 0 means inspection completed, **not** that the import is approved or free of unresolved references. Invalid input exits 2. Each JSON input is limited to 16 MiB; duplicate JSON keys and non-finite constants are rejected.

The consumer checks the declared report envelope, content seal, unique identities, referenced candidates and status/selection consistency. It does not reimplement the mapper, recompute semantic identity, verify source truth, authenticate a report, audit equivalence decisions, or replace the separate conservation auditor. A content seal is an integrity binding, not a signature.

Output preserves both snapshots, including unknown extensions. It distinguishes changed originals under a reused revision, occurrence re-keying, entity changes, equivalence-membership labels and duplicate multiplicity. It retains new, removed, changed and still-unresolved references. A changed selector is distinguished from a silent target change; deleting an unresolved reference is not reported as resolving it.

## Executed validation and visual review

`import-execution.json` records 42 passing driver/loader/consumer tests under normal Python and 42 under real `python -O`, plus source identities and observed output. Consumer unit fixtures are explicit report doubles. The separate demonstration executes the actual LODESTONE mapper and generated identical five-file bundles in normal and optimized Python.

The generated HTML was rendered in Chromium at 1280-by-900 and 390-by-844 viewports. Full-page screenshots were opened and inspected. No overlapping cards, clipped headings or page-level horizontal overflow was observed. The mobile table intentionally scrolls locally. The browser observed zero scripts, external requests and page errors, including opening the full-snapshot disclosure. Rendering used `page.set_content` with the exact generated HTML; no file-URL navigation or browser policy change. These observations are not screen-reader testing or a WCAG certification.

## Attribution and integration

ZZ-CIRRUS / GPT-6 Astra Pro; operation `uiowa-103-cirrus-20260919`; issue #16176; PR #16248. This is a read-only consumer and conformance extension. LODESTONE/#16162 owns the canonical mapper and #16260; QUARTZ owns component/replay adapters; HALYARD owns equivalence review; KESTREL owns conservation and CLI repair. Their occupied paths are untouched.

Publication is distinct from main integration. Exact-current-base and successful hosted execution authority must be verified separately. No local test or browser result in this kit represents a queued GitHub Actions run as successful.
