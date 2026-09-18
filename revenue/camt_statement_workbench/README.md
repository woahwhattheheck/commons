# Bank-statement intake workbench

Turn retained camt.053 XML into an inspectable entry ledger, separately linked transaction details, and an exception report. Everything runs offline using Python's standard library. It does not log in to a bank, initiate payments, post a journal, or change an ERP.

## Run the synthetic demonstration

From the repository root, using Python 3.13 (the tested runtime):

```sh
python -B -m revenue.camt_statement_workbench build \
  --out /tmp/camt-review-new \
  revenue/camt_statement_workbench/fixtures/synthetic-v02.xml \
  revenue/camt_statement_workbench/fixtures/synthetic-v08.xml
python -B -m revenue.camt_statement_workbench verify /tmp/camt-review-new
```

The output directory must not already exist, even if empty. Its parent must exist and be controlled by the operator. Open `review.html` locally. These fixtures are fictional, not bank-issued or independently XSD-certified samples. Expect two statements, six entry rows, four underlying detail records, and a GBP 275 net increase in each separate synthetic account. Do not combine the accounts into a claimed cash balance.

The package can also be copied without the rest of this repository and run as `python workbench.py build --out NEW_DIR EXPORT.xml`. No installation, server, account, or network connection is required. The source uses modern Python syntax; runtimes other than the tested version require their own acceptance run.

## What the outputs mean

| File | Use |
| --- | --- |
| `normalized.json` | Canonical typed interface. Monetary values are exact decimal strings; missing values remain null. Contains source, account, statement, entry, detail, balance and finding lineage. |
| `entries.csv` | Human review of the entry layer. Only a direct `Ntry/Amt` is an entry amount. |
| `details.csv` | Underlying transactions linked to an entry; several amount roles can coexist. These are **not additional cash entries**. |
| `findings.csv` | Exception code, explanation, next action, scope and XML path. |
| `review.html` | Self-contained escaped review; no scripts, external fonts, links, tracking or remote assets. |
| `sources/<sha256>.xml` | Exact retained input bytes. All supplied aliases are listed in the manifest. |
| `manifest.json` | Tool version, source identities and hashes/sizes of the other files. Written last. |

CSV is a display export: every populated cell is prefixed with an apostrophe to preserve identifiers and prevent formula interpretation. Do not treat it as an unmodified numeric import. Use JSON for a reviewed target-system adapter.

The verifier rebuilds all derived files from retained source bytes and compares every byte and the complete file set. Updating a forged report's manifest hash does not make the report pass. `BYTE_CONSISTENT` proves consistency with the installed verifier and retained bytes, **not bank authenticity, delivery completeness, correctness of a bank's data, customer acceptance, or posting permission**. A rejected-source bundle can still be byte-consistent; inspect `report_status` separately.

Build exit codes are 0 (`EXTRACTED`), 1 (`REVIEW_REQUIRED`), or 2 (`SOURCE_REJECTED` / input or I/O error). Verification returns 0 on byte consistency, 2 on failure. Scripts must inspect status rather than relabel all successfully written bundles as acceptable bank statements. One malformed source is rejected atomically; good sources may remain in the same review bundle, whose overall status is still `SOURCE_REJECTED`.

## Supported extraction profile

Explicit namespaces: `camt.053.001.02` and `camt.053.001.08`. Only a direct `Document/BkToCstmrStmt` document in UTF-8 is accepted. Version 2 has text entry status and a `BIC` servicer field; version 8 has code/proprietary status and `BICFI`. Other versions, wrappers, DTDs, foreign namespaces, ambiguous critical singletons and incompatible choices are rejected instead of guessed.

The extraction preserves account identifiers and bank metadata, statement/message references, sequences, period and pagination, entry direction/status/reversal, booking and value dates separately, bank references/codes, batch metadata, balance types and dates, and selected transaction references/remittance. Optional information not projected into normalized fields remains in retained XML. This is a documented **subset extractor, not full XSD validation** or a lossless normalized projection of every optional ISO field. It does not validate the entire currency registry, currency-specific minor units, IBAN checksums or bank facility rules.

Money uses nonnegative plain decimal input, at most 18 significant digits and five fractional digits. CRDT produces a positive signed amount; DBIT a negative one. Reversal indication is retained without negating that sign a second time. Detail amounts retain their role and currency; no amount is inferred from a sibling, no FX conversion is performed, and detail amounts never enter entry totals.

Only explicit standard-code `BOOK` entries enter observed booked totals. Pending or proprietary statuses are retained and reviewed. An in-file balance comparison needs exactly one compatible OPBD opening and CLBD closing balance, consistent dates/currency, and no page/status/period ambiguity. Available balances are not substitutes. A transposed closing code is not silently repaired. `ARITHMETIC_MATCH` means only opening plus observed booked entries equals closing in that supplied statement/currency.

Identical source bytes are parsed once with all aliases retained. Repeated statement/account identities and bank references are flagged while records remain visible. These warnings are deliberately conservative when bank metadata is incomplete. There is no persistent import-history database, cross-file page assembler or automatic reissue resolution. A complete-looking page does not prove the bank delivered every page.

## Operator acceptance before a real integration

1. Obtain authorized exports and the bank's exact facility/version guide through the buyer's approved secure channel. Do not commit real exports, account identifiers, narratives or generated bundles to a public repository or shared Slack.
2. Run in a private directory on a controlled machine. The HTML, CSV and retained XML can all contain sensitive financial information. Parent-directory control and normal OS protections remain the operator's responsibility; this is not a hostile-local-user sandbox or encrypted vault.
3. Review rejected sources first, then paging/reissue/status/currency findings, then balances and summaries. Never fabricate a balancing transaction or substitute a value date for a missing booking date.
4. Resolve every material exception against the bank's own records. Match source generations against the buyer's existing import history and define how reruns/corrections are handled.
5. Map the canonical JSON into an independently reviewed target contract. Preserve source/statement/entry identity and decimal strings. The target owner controls accounting classifications, rounding, posting, acceptance and cutover.

The shipped interface only prepares evidence. A real integration and bank-profile acceptance exercise is a separate paid scope; see `PILOT.md`.

## Resource limits and tests

Inputs are bounded to 32 aliases, 8 MiB per source and 32 MiB aggregate. XML is limited to 150,000 elements/source, depth 48, 64,000 characters per text leaf and 32 attributes/element. Serialized output is capped at 128 MiB **after construction**; that is not a peak-memory guarantee. New output targets, regular files, no symlink members and exact file sets are required. An interrupted write can leave a partial directory; preserve it for diagnosis and rerun into a new directory rather than overwrite.

```sh
python -B -m unittest revenue.camt_statement_workbench.test_workbench -v
python -O -B -m unittest revenue.camt_statement_workbench.test_workbench -v
python -B -m revenue.camt_statement_workbench.benchmark --entries 5000
```

`VALIDATION.md` records the actual local evidence and its limits. `SOURCES.md` records the primary format references. No new CI workflow or recurring task is installed by this package.
