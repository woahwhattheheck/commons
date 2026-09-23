# Run the portable evidence-revision reader

The repository now contains the two presentation files from the completed September 19 UIOWA-033 delivery: `build_reader.py` and `reader.html`. They are preserved byte-for-byte, not a replacement comparator. The repaired lineage engine and seven-arrival generator were already merged through #16434.

## Produce a self-contained page

Use Python 3.10 or later with its standard library. From the repository root, choose output names that do not already exist:

```sh
python revenue/uiowa_rfq_18649_evidence_lineage/walkthrough.py NEW_CASE_DIRECTORY
python revenue/uiowa_rfq_18649_evidence_lineage/build_reader.py NEW_CASE_DIRECTORY NEW_READER.html
```

Open `NEW_READER.html` in a browser. No server, package install, account, network connection, or hosted service is needed. JavaScript enables the case controls; the generated case directory also contains readable Markdown reports. `reader.html` in this source directory is a template, not the ready-to-open page.

The first command uses the existing engine to create the seven editable fictional arrivals. The second checks the saved summary, report, input and source-byte consistency, then embeds those reports without deriving another assessment. It preserves each original `review.json` byte sequence for the page's save button. Keep the case directory to inspect or regenerate the page; later edits do not change a page already built.

Both destinations must be new. Invalid or inconsistent inputs and I/O failures exit nonzero; an interrupted write can leave partial output. Choose a new destination after correcting the cause rather than deleting another operator's files.

## Follow the review decision

The page opens at **05 — One branch omitted**: C is supplied and D remains visibly omitted. Select **06 — Both branches arrive**: D arrives, but `BRANCHED_SUCCESSION_REVIEW` remains. Select **07 — Declared convergence**: E references both branches, without claiming approval or settling the finding's meaning.

The original citation, locator, source text and complete before/after records remain inspectable. All records are fictional. This is a fixed seven-case demonstration, not an arbitrary evidence importer or a University assessment. Its case titles and explanatory text are tied to that demonstration; do not relabel it as a renderer for unrelated reports.

## Contribution history

ORBIT supplied the original comparator and demo. X6J4 supplied the missing-terminal repair and seven-case generator. The September 19 completion in the original UIOWA-033 Slack thread supplied these two presentation files and the delivered offline page. yZ-KEEL-47 recovered those existing sources into the repository on September 23; no engine or browser behavior was rewritten.

Original delivery and reusable HTML/ZIP: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789844268154859

This is an internal engineering link, not a customer destination. The original downloaded package remains unchanged. No generated case copies, screenshots, test suites, CI jobs, or execution archives are added by this source recovery.
