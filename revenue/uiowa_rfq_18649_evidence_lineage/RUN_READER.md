# Run the portable evidence-revision readers

The repository contains the two presentation files from the completed September 19 UIOWA-033 delivery: `build_reader.py` and `reader.html`. They are preserved byte-for-byte, not a replacement comparator. The repaired lineage engine and seven-arrival generator were already merged through #16434. For ordinary saved comparison reports, use the separate reader described below.

## Produce the seven-arrival demonstration

Use Python 3.10 or later with its standard library. From the repository root, choose output names that do not already exist:

```sh
python revenue/uiowa_rfq_18649_evidence_lineage/walkthrough.py NEW_CASE_DIRECTORY
python revenue/uiowa_rfq_18649_evidence_lineage/build_reader.py NEW_CASE_DIRECTORY NEW_READER.html
```

Open `NEW_READER.html` in a browser. No server, package install, account, network connection, or hosted service is needed. JavaScript enables the case controls; the generated case directory also contains readable Markdown reports. `reader.html` in this source directory is a template, not the ready-to-open page.

The first command uses the existing engine to create the seven editable fictional arrivals. The second checks the saved summary, report, input and source-byte consistency, then embeds those reports without deriving another assessment. It preserves each original `review.json` byte sequence for the page's save button. Keep the case directory to inspect or regenerate the page; later edits do not change a page already built.

Both destinations must be new. Invalid or inconsistent inputs and I/O failures exit nonzero; an interrupted write can leave partial output. Choose a new destination after correcting the cause rather than deleting another operator's files.

## Follow the review decision

The seven-arrival page opens at **05 — One branch omitted**: C is supplied and D remains visibly omitted. Select **06 — Both branches arrive**: D arrives, but `BRANCHED_SUCCESSION_REVIEW` remains. Select **07 — Declared convergence**: E references both branches, without claiming approval or settling the finding's meaning.

The original citation, locator, source text and complete before/after records remain inspectable. All records in that demonstration are fictional. Its case titles and explanatory text are tied to the seven saved cases; do not relabel it as a renderer for unrelated reports or a University assessment.

## Review an ordinary saved comparison

`review_reader.py` and `review_reader.html` provide a separate presentation for any structurally valid `uiowa.evidence-lineage.v1` comparison report. They do not require synthetic input, seven cases, one finding, or embedded example passages.

```sh
python revenue/uiowa_rfq_18649_evidence_lineage/review_reader.py PATH_TO_REVIEW.json NEW_FINDING_REVIEW.html
```

Use JSON already produced by `lineage.py compare`, `demo.py`, or `walkthrough.py`. The reader checks the report's rendering contract with the engine's existing JSON and manifest validation routines. It does **not** rerun the comparison, independently check source-byte assertions, authenticate an approval, or change a finding. Its displayed statuses and summary are supplied report data. Input is read once, up to the engine's 16 MiB input limit. Invalid input and I/O errors exit 2 with an explanation. Existing outputs are never overwritten.

Open the generated HTML, not the `review_reader.html` source template. Search the impact queue by finding ID, citation, locator, or status; combine that with the reported-status selector. Each citation impact remains a separate row, including citation-free findings. Supplied declared successors, known but omitted successors, and retained exact copies stay distinct.

Follow a source link to reveal its full record. Links resolve by **record ID plus digest**, so a reused ID cannot silently point to different bytes. Records with no embedded passage show that limitation rather than inventing text from a locator. Complete original findings, both source collections, changes, departures, duplicate groups, anomalies, and the full original report remain available in expandable sections.

The **Save original JSON bytes** button preserves the exact input file, including its original formatting and numeric text. The document is pre-rendered, so the report remains readable without JavaScript; filtering, automatic source expansion, and download need JavaScript. No report is uploaded or stored in browser storage. All source locations are inert text; the page does not fetch them.

**Sharing the HTML shares the whole report and its metadata.** Use the same handling rules as the source evidence. Non-synthetic reports are not University findings merely because this reader presents them. Neither reader edits evidence or records review decisions. To present a later report, build a new HTML file.

## Contribution history

ORBIT supplied the original comparator and demo. X6J4 supplied the missing-terminal repair and seven-case generator. The September 19 completion in the original UIOWA-033 Slack thread supplied the original two presentation files and delivered offline page. yZ-KEEL-47 recovered those existing sources on September 23, then added the separate ordinary-report reader without rewriting the engine or original presentation.

Original delivery and reusable HTML/ZIP: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789844268154859

This is an internal engineering link, not a customer destination. The original downloaded package remains unchanged. No generated case copies, screenshots, test suites, CI jobs, or execution archives are added by these reader changes.
