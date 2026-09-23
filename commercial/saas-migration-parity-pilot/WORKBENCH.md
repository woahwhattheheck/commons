# Export workbench

Use the existing SaaS Migration Parity Pilot engine from a browser, with explicit CSV/JSON intake and field mapping. The command-line engine remains unchanged.

## Start

From this directory, with Python 3.10 or newer:

```bash
python workbench.py --port 8767
```

Open the printed `http://127.0.0.1:8767/` address on the same machine. `--port 0` chooses an available port. Stop the process with Ctrl+C. This is a local operator tool, not a public hosted service; it listens only on IPv4 loopback. In a cloud development environment, use that environment's existing loopback access route. Do not expose it as a public customer endpoint.

No third-party packages, external assets, SaaS credentials, API calls to external services, upload directory, or persistent job store are required. Missing assets or a bind failure produce `ERROR:` on stderr and exit code 2. Invalid requests produce a non-success HTTP status and a visible browser error rather than a successful report.

## Complete a comparison

1. Load the sanitized source and target exports. Inspection shows field names and record counts without displaying record values. Select CSV or JSON; a recognized filename extension only selects the format, not field types or snapshot metadata.
2. Enter distinct snapshot IDs, schema revisions, and the actual capture instants in `YYYY-MM-DDTHH:MM:SSZ` form. Declare completeness only for the agreed export scope. Replacing a file clears that side's capture time and completeness declaration.
3. Set the cutover instant and maximum snapshot age in seconds. The current-UTC button changes only cutover; upload time and file modification time never stand in for capture time.
4. Explicitly select 1–4 record-key mappings and 1–32 compared-field mappings. Field selection starts blank. Choose `string`, `integer`, or `boolean` for compared fields; keys support string and integer only. Replacing an export resets mappings so old choices are not silently applied to different data.
5. Compare. Filter classifications, search by opaque key, field name or reason, and open mismatch details to inspect value digests. Rows are paginated in groups of 50.
6. Download the generated input JSON, exact report JSON, report Markdown, or printable HTML as needed. Editing any input invalidates the displayed result and every download link. A late response for changed inputs is discarded rather than presented as current.

Unchecked completeness, stale/future snapshots, duplicate keys, missing or unexpected records, and differences retain the existing engine's classifications. The workbench does not override these states or infer that an omitted record does not exist.

## Portable browser report

Choose **Download printable HTML** for a report that opens directly in a browser without Python, a running server, or network access. It includes snapshot metadata, explicit mappings, counts, classification/search controls, all row-level reasons and mismatch digests, and an exact JSON download. All results remain readable when JavaScript is disabled; only the interactive controls require it.

Printing includes **every report row**, even when screen filters hide some rows. The page states this beside the controls and in the footer, so a filtered screen is not silently presented as a complete printed result.

The embedded JSON is base64-encoded from the canonical report bytes and decoded directly into a download. It is not parsed and re-serialized through JavaScript. Inline scripts and styles have content hashes in a restrictive Content Security Policy; no external resources or network connections are requested.

This document is a presentation of the compiled report, not a signature, an independent verification run, or a production-cutover certification. Editing an HTML file can change its presentation; the reported digest is not a substitute for checking the supplied manifest with the existing offline verifier. The HTML contains report metadata and digests, **not the input manifest's record values**. Protect it nonetheless: hashes do not guarantee anonymization.

The same portable output is available from an existing engine manifest without starting the workbench:

```bash
python offline_report.py \
  --input parity-input.json \
  --report-json new-report.json \
  --report-html new-report.html
```

Both output paths must be new. This command reuses the existing bounded input reader, comparison engine and paired create-exclusive writer. Browser downloads use the browser's save mechanism and do not claim the CLI's descriptor-relative filesystem guarantees.

## Export formats

CSV is UTF-8 with a header row. A leading UTF-8 BOM is accepted. JSON is a UTF-8 array of flat objects, not a prebuilt engine manifest. JSON duplicate keys, floating-point numbers and non-finite numbers are rejected by the existing strict parser.

Each export is limited to 500 records and 4,000,000 UTF-8 bytes. At most 64 distinct field names are accepted. Column names must start with a letter and contain only letters, digits, `.`, `_`, or `-`, up to 64 characters. CSV row widths must match the header; duplicate headers or excess records are errors, not silently repaired or truncated. The generated combined engine manifest must also fit the existing 4,000,000-byte limit.

The engine accepts nonempty strings, signed 64-bit integers and booleans. Blank strings, nulls, nested data and control characters are not silently discarded. Resolve unsupported cells in the explicitly agreed sanitized export before loading it; the workbench does not fill in missing facts.

**CSV types are explicit.** String cells retain their bytes after CSV decoding: no trimming, case folding or numeric guessing. Mapped integer cells must use decimal digits with an optional minus sign, no whitespace, and no leading zeros other than zero itself. Mapped boolean cells must be exactly `true` or `false`. Use string for identifiers with leading zeros. Unmapped CSV cells remain strings. Declaring conflicting types for the same key/compared field is an error.

**JSON types are retained.** Integer identifiers never pass through JavaScript's number parser: the browser sends the original export text, Python parses it, and the server returns the generated manifest as an exact string. A JSON string is not silently converted to an integer because a mapping asks for integer; the engine reports the type mismatch. Likewise, booleans are not integers.

## Download fidelity and privacy

The downloaded input is a **generated normalized engine manifest**, not a byte-for-byte copy of either original export. Its `raw_input_sha256` in the report binds that generated manifest. Preserve original export files separately when original-file provenance matters.

The workbench uses `parity.compile_bytes()` for results and `canonical_bytes()` for the report. Downloads preserve the returned strings without parsing and serializing the manifest in JavaScript. The existing CLI can consume them directly:

```bash
python parity.py verify --input parity-input.json --report-json parity-report.json
```

The server retains no upload or report files between requests. The page holds loaded export text and download blobs in browser memory; clear-session removes its references and revokes download URLs. This is not a secure-memory-erasure guarantee. Browser history, browser extensions, operating-system memory, and files already downloaded are outside the workbench's control. Clearing the page never deletes downloaded files.

The input download contains supplied field values. Report key/value commitments are hashes, not encryption or guaranteed anonymization. Protect all exported artifacts accordingly. No external provider, customer contact, production migration, contract, payment, or revenue-recognition action is performed.

## Files

- `export_intake.py`: strict export parsing and explicit CSV conversion into the existing manifest.
- `workbench.py`: stateless loopback HTTP transport and calls into the existing comparison engine.
- `workbench.html` and `workbench.js`: responsive operator interface, explicit mapping, result browsing, and exact downloads.
- `offline_report.py`: self-contained printable HTML presentation plus an existing-manifest CLI route.

Original product and comparison-engine lineage remains documented in `README.md`. This workbench adds an operator route; it does not replace that implementation or the existing commercial/outbound ownership.
