# Cashiering CSV intake and replay

The CSV intake command assembles explicit normalized tables into the existing cashiering input contract, then uses the existing reconciliation engine and artifact generator. It completes the flat-export assembly continuation for [Commons #15882](https://github.com/woahwhattheheck/commons/issues/15882). Original acceptance-lab donor credit remains with Z-Kestrel-TN59; the broader Tennessee pursuit remains with its existing owners.

Use an upstream mapper, including the existing generic CSV workbench tracked in SMB #1494 where appropriate, to produce these normalized fields. This adapter defines the final table and join contract. It does not infer a source export's column meanings, money signs, currency scales, time cutoffs, accounting allocations, original receipt links, or completeness. No private SMB implementation or customer data is included here.

## Run the retained examples

Run these commands from the acceptance-lab directory with Python 3.10+ on a supported POSIX filesystem. Each output directory must be new, and its parent must already exist.

```sh
python -m cashiering_lab.csv_intake split examples/clean.json --out /tmp/cashiering-csv-clean-source-new
python -m cashiering_lab.csv_intake compile /tmp/cashiering-csv-clean-source-new --out /tmp/cashiering-csv-clean-handoff-new
python -m cashiering_lab.csv_intake verify /tmp/cashiering-csv-clean-handoff-new
```

`split` validates the existing normalized JSON and emits the seven-file source directory described below. This gives an operator complete headers and an editable normalized example. `compile` retains those source bytes and builds the native review bundle. Open `review/report.html` inside the handoff to read the report; its sibling JSON and CSV files expose the same review data.

The existing exception specimen exercises the same workflow with retained economic findings:

```sh
python -m cashiering_lab.csv_intake split examples/exceptions.json --out /tmp/cashiering-csv-exceptions-source-new
python -m cashiering_lab.csv_intake compile /tmp/cashiering-csv-exceptions-source-new --out /tmp/cashiering-csv-exceptions-handoff-new
python -m cashiering_lab.csv_intake verify /tmp/cashiering-csv-exceptions-handoff-new
```

The exception specimen's `compile` command returns 1 after writing its usable handoff. Run `verify` separately when using a shell that stops on nonzero exit codes. Verification succeeds when the retained exception report replays exactly; it does not change the report to a clean result.

| Command | Exit 0 | Exit 1 | Exit 2 |
| --- | --- | --- | --- |
| `split` | Valid normalized input emitted as source tables | Unused | Malformed input or filesystem error |
| `compile` | Report has no findings in supplied data | Report retains economic findings | Malformed source, ambiguous assembly, or filesystem error |
| `verify` | Complete handoff matches exact replay, with or without findings | Unused | Invalid, incomplete, changed, or unreadable handoff |

The source produced by `split` is a representation of the JSON's values. It does not retain the original JSON's whitespace or byte identity. The subsequent handoff retains the actual `case.json` and CSV bytes supplied to `compile`.

## Source directory

The directory must contain exactly these seven regular files. Keep all six CSV files, including their headers when a table has no rows. Extra files, missing files, or unsupported file types prevent compilation.

| File | Contents |
| --- | --- |
| `case.json` | The five document metadata fields |
| `batches.csv` | One row per batch |
| `transactions.csv` | One row per transaction, excluding its nested components |
| `tenders.csv` | One tender component per row, joined through `transaction_id` |
| `allocations.csv` | One accounting component per row, joined through `transaction_id` |
| `deposits.csv` | One row per deposit, excluding its batch assignments |
| `deposit_batches.csv` | One deposit-to-batch assignment per row |

`case.json` is strict UTF-8 JSON without a byte-order mark. Its object contains exactly `schema`, `case_id`, `period`, `currency_scale`, and `variance_reason_threshold_minor`. These are the existing document fields from [INPUT_CONTRACT.md](INPUT_CONTRACT.md): `schema` is `cashiering-acceptance/1`, `period` contains explicit `start` and `end`, and `currency_scale` supplies the currency labels and integer scales. Do not include `batches`, `transactions`, or `deposits` in this metadata file; the adapter assembles those arrays from the CSV tables.

### Exact CSV headers

Each CSV must have exactly its listed columns, without duplicate, missing, or extra names. Column order may differ. Header names are case-sensitive and are not trimmed.

`batches.csv`:

```csv
id,agency,business_unit,department,location,bank_account,currency,cashier,opened_at,closed_at,opening_cash_minor,counted_cash_minor,retained_cash_minor,declared_total_minor,variance_reason
```

`transactions.csv`:

```csv
id,batch_id,kind,timestamp,original_id,original_minor,rounding_minor,collected_minor,evidence_ref
```

`tenders.csv`:

```csv
transaction_id,type,amount_minor
```

`allocations.csv`:

```csv
transaction_id,account_id,amount_minor
```

`deposits.csv`:

```csv
id,agency,business_unit,department,location,bank_account,currency,tender,observed_minor,variance_reason,evidence_ref
```

`deposit_batches.csv`:

```csv
deposit_id,batch_id
```

### Cell values

CSV uses a comma delimiter, double-quote quoting, and strict UTF-8. An optional UTF-8 byte-order mark is accepted at the start of a CSV file. Quote embedded commas and escape a double quote by doubling it. Decoded values are not trimmed, reformatted, or evaluated as spreadsheet expressions. Quoting does not relax the engine's restrictions on control characters or accepted field values.

Source tables preserve values verbatim, including formula-like text. Import them as text when editing in a spreadsheet. The generated review CSVs retain the engine's formula escaping.

An empty cell means JSON `null` only for the following fields:

| File | Nullable fields |
| --- | --- |
| `batches.csv` | `counted_cash_minor`, `declared_total_minor`, `variance_reason` |
| `transactions.csv` | `original_id` |
| `deposits.csv` | `observed_minor`, `variance_reason` |

An empty required cell remains empty and fails validation where the contract requires a value. The literal text `null` is not a null marker. Use an explicit `0` for a known zero amount; a missing drawer count or observed deposit must remain missing.

Every amount uses integer minor units matching `-?(0|[1-9][0-9]*)`. Examples of accepted representations are `0`, `12500`, and `-500`. Leading plus signs, leading zeros, decimal points, grouping separators, exponent notation, and surrounding whitespace are rejected. Do not convert money through floating point or let a spreadsheet change an identifier or timestamp. The engine separately enforces the amount bound and nonnegative cash-count/float fields.

Use exact normalized transaction kinds `RECEIPT`, `REFUND`, and `REVERSAL`, and tender types `CASH`, `CHECK`, `CARD`, `ACH`, and `OTHER`. All six scope fields must be supplied for each batch and deposit. Timestamp offsets, identifier syntax, evidence references, and accounting rules retain the requirements in [INPUT_CONTRACT.md](INPUT_CONTRACT.md).

## Joins and findings

IDs join rows by their supplied values. Batch, transaction, and deposit IDs must each be unique within their own table. Every transaction's `batch_id` must identify a retained batch. Every tender and allocation row must identify a retained transaction. Every deposit assignment must identify both a retained deposit and a retained batch. Orphan rows are rejected rather than dropped.

Each transaction needs at least one tender component and at least one allocation component. Tender types and account IDs must be unique within that transaction's corresponding component collection. Each deposit needs at least one batch assignment, and repeating the same batch within one deposit is rejected. At least one batch is required; the transaction and deposit tables may be empty when that accurately represents the supplied period.

The existing engine still decides economic findings after assembly. For example, an invalid original receipt reference, reused declared evidence, component totals that disagree with collected amounts, or reuse of a complete batch/tender across different deposits remains visible in the report. CSV assembly does not silently repair those rows or promote them to a clean result. A deposit scope mismatch and missing drawer/deposit amounts retain the engine's existing treatment as well.

## Handoff contents and replay

The generated handoff retains the seven source files under `source/`, `lineage.json`, `manifest.json`, and the native eight-file bundle under `review/`.

| Location | Purpose |
| --- | --- |
| `source/case.json` and the six source CSV files | Exact input bytes used for assembly |
| `lineage.json` | A `locations` array tying assembled JSON pointers to source filenames and physical line ranges, with the assembled input hash |
| `manifest.json` | Byte counts and hashes for every source, review and lineage file |
| `review/input.json` | Assembled normalized JSON supplied to the engine |
| `review/report.json`, `batches.csv`, `deposits.csv`, `transactions.csv`, `exceptions.csv`, `report.html` | Native reconciliation output |
| `review/manifest.json` | Native eight-file bundle manifest |

CSV line ranges use 1-based `line_start` and `line_end` to identify the physical first and last lines of a parsed row, so a quoted CSV record spanning lines can be traced to its retained bytes. The five metadata pointers reference the whole retained `case.json`. Lineage identifies how values were assembled; it does not establish that the source export was authentic or complete.

`python -m cashiering_lab.csv_intake verify HANDOFF` rebuilds the handoff from its retained source and compares the full result. Missing, extra, or changed files fail exact replay, including changes to retained CSV formatting that might otherwise assemble to the same values. The existing `python -m cashiering_lab verify HANDOFF/review` remains available for the native bundle alone; use the CSV intake verifier to include the source retention and lineage in verification.

To correct a source table, edit a separate working source directory and compile a new handoff. Preserve the earlier handoff when its historical contents matter. Regenerating an entire handoff from changed input can produce another internally consistent result; replay hashes do not attest an external source or establish custody on their own.

## Bounds and filesystem behavior

The seven source files together may contain at most 8 MiB. Assembled normalized JSON is also limited to the engine's 8 MiB maximum. Each CSV accepts at most 80,000 data rows. The engine's stricter applicable limits still apply: at most 20,000 combined batches, transactions, and deposits; at most 100 tender components and 100 allocation components per transaction; and at most 80,000 tender/allocation components in total. Individual deposit assignment lists retain the engine's 20,000-row limit.

Commands use new, exclusively created output directories and require POSIX directory descriptors with no-follow access for child files. Parent directories must be trusted against concurrent replacement. An interrupted or failed write can leave an incomplete directory; inspect it and use a new output path for a retry. Exact verification rejects incomplete output. This protection does not make the filesystem a hostile-host sandbox or provide a concurrent immutable snapshot.

These commands run offline with the existing standard-library package. They perform no bank access, payments, refunds, accounting posting, provider setup, or external contact. Retained reports concern normalized supplied data under this engine; they do not certify State, bank, customer, compliance, or production acceptance. Keep customer exports outside this public repository and use an approved delivery surface for customer handoffs.
