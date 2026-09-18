# AP evidence review workbench

An executable, offline review and delivery surface for the existing v2 AP invoice
compiler. It does not replace the source-ledger or procurement compiler. It turns
normalized USD invoice cases into a human-readable exception table, exact-cent CSV,
replayable JSON report, and a byte manifest. A finance reviewer can inspect an
exception without needing to read a Python receipt object.

## Run from the repository root

Python 3.11+ and a POSIX filesystem are required for the file commands. There are
no third-party dependencies, network requests, accounts, or external writes.
Choose a new output directory; an existing file, directory, or symlink is refused.

```sh
python revenue/opportunities/unc_ap_ai_peoplesoft/ap_review.py build \
  --input revenue/opportunities/unc_ap_ai_peoplesoft/examples/review_intake.json \
  --out /tmp/ap-review-example
python revenue/opportunities/unc_ap_ai_peoplesoft/ap_review.py verify \
  --out /tmp/ap-review-example \
  --against revenue/opportunities/unc_ap_ai_peoplesoft/examples/review_intake.json
```

Open `review.html` locally. It is self-contained, has no script or external links,
and makes no network requests. `review.csv` is the row-level exception/review table;
`review.json` retains normalized inputs and the exact v2 result for every invoice;
`manifest.json` identifies every output byte. The manifest is written last.
A crashed or incomplete write is not a completed pack. Verification requires all
four expected files and rejects extras, symlinks, modifications, and missing files.

The example is **synthetic**: one consistent invoice and two opposite one-cent
amount errors. Net difference is zero; absolute differences total two cents and
both errors remain visible. Nothing is posted, approved, invoiced, or paid.

The CLI exits zero when it successfully constructs or verifies a report, including
a report with exceptions. The printed report status is separately `CONSISTENT` or
`REVIEW_REQUIRED`. Exit two means invalid input, refused output, or verification
failure. A successful command is never permission to pay or submit a proposal.

## Input and interpretation

The top-level input has exactly `schema` (`unc.ap-review-input/v1`),
`evidence_class` (`SYNTHETIC` or `OPERATOR_SUPPLIED_UNVERIFIED`), `currency` (`USD`),
`extraction_threshold_basis_points` (integer 0 through 10000), and `cases`.
Every case uses the existing v2 invoice contract; see the checked-in example.
The threshold is an operator policy input, not a claimed buyer requirement.

The wrapper admits 1 to 1000 cases and at most 2 MiB of UTF-8 JSON. Monetary input
is integer cents in the nonnegative signed-64-bit range, with exact integer
aggregation even when a total exceeds that range. Floats, exponents, non-finite
numbers, duplicate decoded JSON keys, unknown fields, object subclasses, cyclic
structures, excessive depth, and unsafe identity text are rejected. Identities
must be nonblank NFC strings without control characters or surrounding whitespace.

Supplier plus invoice is the business identity. The same invoice number may
legitimately occur for different suppliers. A repeated supplier/invoice pair or
shared supplied integration effect key is rejected rather than silently discarded.
Use the v2 `expected_integration_evidence` helper **only for synthetic fixtures**;
production observations must not be regenerated to make failures disappear.
Rows are ordered by supplier and invoice, so reordered input has the same semantic
receipt. No input object is mutated.

The summary distinguishes signed net difference from the sum of absolute line
differences. Expected amounts attached to exception rows are review context, not
proven loss, savings, receivables, or recoverable exposure. An aggregate match is
not a reason to discard individual mismatches. This version checks aggregate
invoice/PO/receipt amount parity, not line-level quantities, tax, FX, or OCR itself.

CSV identifier cells beginning with formula characters are prefixed with an
apostrophe, and all fields are quoted. Integer cents are exported exactly as text
bytes. When opening in spreadsheet software, import large integer columns as
**text** to avoid that software's numeric precision conversion. JSON is the
canonical machine-readable record; CSV is not an accounting import instruction.

## What verification establishes

`verify_review` recompiles every row, summary, authority flag, and receipt from the
retained normalized input using the installed v2 engine. A changed total,
disposition, or authority flag still fails after someone recomputes a superficial
hash. `verify_pack` additionally regenerates CSV, HTML, JSON, and the manifest and
compares every retained byte. Engine source SHA-256 is part of the report; an
engine change requires a new report instead of silently verifying old semantics.

Supply `--against` to verify that the report uses the particular original input
you retained. Without it, verification proves only consistency with the embedded
input, not that the original was authentic or that somebody did not replace the
entire input and recompute a different consistent report. Neither mode authenticates
a PeopleSoft response, source-system records, user identity, or a procurement
source package. Normalized operator input remains explicitly unverified.

The runtime, installed source, and filesystem ownership are trusted. This is not
a defense against arbitrary in-process code execution or an administrator replacing
Python. Input reads use bounded regular-file descriptors with no-follow and
before/after metadata checks. Output directories are mode 0700 and files 0600;
no existing path is overwritten. Ancestor-directory ownership and safe retention
of sensitive input remain the operator's responsibility. JSON includes the input
case evidence; do not send it to unrelated recipients or publish real buyer data.

## Testing and integration

```sh
python -m unittest -v test_unc_ap_ai_peoplesoft.py
# Or from this package directory:
python -m unittest -v test_ap_review.py
python -O -m unittest -v test_ap_review.py
```

The existing root hook discovers at least 116 tests: source and correlation,
Cairn batch identity, and the 71-test review surface. It refuses a vacuous or
skipped suite and executes both normal and real optimized Python. No Actions workflow is added;
it participates in existing root test discovery. Hosted execution must be reported
separately from local cloud execution.

The implementation is additive (`ap_review.py`, its tests, this guide, the example,
and the root hook). It composes with Cairn's supplier-scoped batch/receipt correction
rather than overwriting the engine. Original product/source credit: Z-Sol and
Z-Ledgerwake; source recovery: Z-ObliqueLedger-0230; batch correction: Z-Cairn-UNC;
review workbench: Z-Fenwick-R8 / GPT-6 Astra Pro.

## Paid-delivery use

Use this workbench as the reviewable handoff inside the existing **$12,000 proposed,
not accepted** AP/PeopleSoft acceptance-workshare hypothesis, not as a second offer
or free production-integration commitment. A paid pilot needs an agreed statement
of work covering the permitted input mapping, a bounded acceptance corpus, an
exception-review meeting, and one retained replay pack. Scope, staffing, schedule,
legal terms, and payment milestones are commercial inputs, not generated facts.
A prime or buyer owns real system access, record authority, compliance obligations,
accounting decisions, and any production release. No sale, payment, partnership,
reference, certification, or successful procurement is asserted by this tool.
