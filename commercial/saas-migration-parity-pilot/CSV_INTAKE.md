# CSV intake for the SaaS Migration Parity Pilot

Run a complete retained-export comparison without hand-authoring the engine's nested record JSON. The browser and CLI call the existing `parity.compile_bytes()` implementation; no parity rule, commercial offer, provider integration, or existing report schema is changed.

## Browser workflow

From a checkout containing this directory and its existing Python modules:

```sh
cd commercial/saas-migration-parity-pilot
python3 web_intake.py --port 8765
```

Use Python 3.10 or newer. Open the exact `http://127.0.0.1:8765/` address printed by the process. Use `--port 0` to choose a free local port. The service binds only to IPv4 loopback; it is not a hosted or multi-user deployment. Stop with Ctrl-C. It requires only the Python standard library and the existing sibling modules. Do not put it behind a public proxy.

1. Select a retained source CSV and target CSV, choose their delimiters, and press **Read columns**. UTF-8 with an optional BOM is supported. Inspection shows headers and record counts, not row values.
2. Add 1–4 composite identity columns and 1–32 compared fields. Select each source/target header and its type. No mapping is inferred from similar names. Duplicate key rows are preserved for the engine to classify.
3. Enter distinct snapshot identifiers, schema revisions, captured-at times, the intended comparison cutover and maximum snapshot age. Times must use exact UTC seconds, such as `2026-09-23T08:00:00Z`. Completeness checkboxes start unchecked. They are operator declarations, not proof the export includes every live record.
4. Compare and inspect all differences and holds. Filter the displayed union-key rows by classification. Download report-only JSON/Markdown or the original-to-alias column map. The **Private replay ZIP** additionally contains selected raw values needed to recompile the result.

Changes to any input invalidate displayed results and download links. Changing a file or delimiter requires inspection again. Save an intake plan to repeat the same mapping; load it before reading the next pair of CSVs, and explicitly update/reconfirm its dates and snapshot facts. Import is a convenience, not attestation of those facts.

The app has no analytics, external assets, provider calls, cookies, local storage, background polling, or persistent server upload directory. CSVs and results are processed in browser/process memory. This is not secure-memory erasure: operating-system swap, browser tooling, and downloaded files are outside that claim. **Clear session** drops the page's working references and download links; it does not delete downloads. Restarting the server changes its per-launch request token.

## Exact conversion behavior

Each file is bounded to 4,000,000 bytes, 500 data records and 64 columns. Delimiters are comma, semicolon or tab, selected separately for each file. Quoting uses Python's strict CSV reader. Duplicate/empty headers, headers over 256 characters, control characters in headers, malformed quoting, and inconsistent row widths are rejected. Blank physical records are not silently removed. Header-only exports are supported; the engine's declared-completeness and freshness rules still apply. The generated engine input also has its existing 4,000,000-byte bound.

Strings are preserved byte-decoded, with no trimming, case folding, date guessing, numeric normalization or Unicode normalization. Mapped strings must be nonempty, at most 2048 characters and contain no control characters. Empty cells are not inferred as null. Integer conversion accepts only optional minus plus unpadded decimal digits in signed 64-bit range; it rejects fractions, exponents, spaces and padded identifiers. Use string for identifiers such as `001234`. Boolean conversion accepts only lowercase `true` or `false`; booleans cannot be key columns. Unmapped values are not interpreted or compared. CSV formulas are treated as strings, never evaluated; no CSV result file is generated.

CSV header names need not fit the engine's field-name grammar. The adapter maps them to `key_1`…`key_4` and `field_1`…`field_32` on both sides. The plan and `column-map.json` retain the exact original headers and types, and identify excluded columns. Report hashes and mismatch aliases describe this mapped manifest, not the original CSV representation. Original CSV byte hashes are kept in the column map. Unselected columns are absent from the replay manifest.

Freshness is evaluated at the **declared cutover**, using the unchanged existing engine. This interface does not independently establish a present-time snapshot, live SaaS completeness, or fitness for a production migration.

## CLI and replay

The same adapter supports an export-only command:

```sh
python3 csv_intake.py --source source.csv --target target.csv \
  --plan intake-plan.json --output private-comparison.zip
```

The output path must be new. The CLI creates it with owner-only permissions where supported, never overwrites it, and does not create missing parent directories. A failed write can leave a partial file; choose a new path after addressing the error. Input reads reuse the existing bounded regular-file reader.

Plan shape (illustrative metadata only, not actual export facts):

```json
{
  "schema": "saas-migration-csv-intake/v1",
  "cutover_at_utc": "2026-09-23T08:00:00Z",
  "max_snapshot_age_seconds": 86400,
  "key_map": [{"source": "Record ID", "target": "External ID", "type": "string"}],
  "field_map": [{"source": "Status", "target": "Lifecycle", "type": "string"}],
  "source_snapshot": {
    "snapshot_id": "source-export", "schema_revision": "1",
    "captured_at_utc": "2026-09-23T07:00:00Z", "complete": false, "delimiter": ","
  },
  "target_snapshot": {
    "snapshot_id": "target-export", "schema_revision": "1",
    "captured_at_utc": "2026-09-23T07:05:00Z", "complete": false, "delimiter": ","
  }
}
```

The ZIP contains only five deliverable files: `manifest.json`, `report.json`, `report.md`, `intake-plan.json` and `column-map.json`. It does not bundle the original CSVs or source checkout. Retain the original CSVs separately when their exact byte provenance matters. The engine report is stored in its exact canonical byte encoding; ZIP metadata is not a deterministic engine receipt.

The existing replay entrypoint accepts the extracted manifest and report:

```sh
python3 parity.py verify --input /private/extracted/manifest.json \
  --report-json /private/extracted/report.json
```

This command is available to the operator; no new test runner, test file, workflow, fixture, or validation framework is part of this feature.

## Sharing and lineage

The private replay bundle includes selected raw identifiers and values. Do not publish it or attach it to a public issue. Report-only files omit raw row values, but still contain snapshot metadata, aliases and unsalted commitments; these are not an anonymization guarantee. The column map contains original header names. Review every artifact for the intended recipient.

Original product concept: Z-GrothendieckAnvil-2144-H8C3 (ZGA-H8C3). Original implementation recovery: Z-Sol-01A. CSV/browser delivery: yZ-Quarry-47, under the existing #14205 product. This source feature neither completes the separate commercial outreach lane nor asserts a customer deployment, accepted price, contract, payment or revenue.
