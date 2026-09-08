# Supplier catalog file intake

Demand `bm-hive-20260908-044`. This is a companion to the canonical
`parts-sourcing-desk`, not another desk, database, fit-review engine, or order system.
The existing desk remains the authority for application field validation, imports,
fit review and handoffs.

## Preview a source file

Python 3.10 or later; standard library only. Run in the existing cloud workspace.

```sh
python catalog_file.py supplier.csv --output supplier-preview.json
python catalog_file.py supplier.json --output supplier-preview-json.json
python -m unittest -v test_catalog_file.py
```

The preview command does not contact suppliers or apply database changes. It reads
one bounded byte snapshot and writes a new preview file (or stdout). Existing output
files are left unchanged. Preserve the original file beside the preview in private
operational storage; the preview carries a hash and record locations, not original
file bytes. Do not commit actual supplier/customer files to the public repository.

CSV accepts UTF-8, including a UTF-8 BOM, a nonblank unique header for each column,
quoted commas, quoted multiline values and CRLF. Headers with surrounding whitespace
are diagnosed rather than silently renamed. Blank physical rows are skipped; rows
with missing/extra fields report physical line locations. A quoted empty cell is
still a cell. The parser supports up to 8 MiB and 5,000 data records per source.

JSON accepts an array of nonempty row objects or an object containing only `rows`.
Duplicate object keys and non-finite values are errors. Decimal JSON numbers become
strings preserving decimal precision; part identifiers should be JSON strings so
leading zeros remain explicit. Supplier arrays, such as aliases, remain arrays.
JSON row locations use JSON pointers; they do not claim physical source line numbers.

## Explicit header mapping

A mapping file is a JSON object from supplier column name to canonical field name:

```json
{"SKU": "part_number", "Model": "model", "List price": "unit_price"}
```

Use the field names expected by the current desk importer. A mapping entry whose
source column is absent, or one which would overwrite another field, is an error.
Unmapped columns remain present. Optional defaults fill only absent or empty-string
cells; they never replace an existing supplier value or infer compatibility.

```sh
python catalog_file.py supplier.csv --mapping columns.json \
  --defaults source-context.json --output mapped-preview.json
```

Defaults are explicitly supplied context, not independently verified observations.
Never default a present-day stock/price observation timestamp unless someone actually
observed that information. A filename or matching part/model number is not fit proof.

## Python integration surface

```python
from catalog_file import read_catalog, parse_bytes, map_fields

parsed = read_catalog("supplier.csv")
# For an already-read upload: parsed = parse_bytes(raw_bytes, "supplier.csv")
rows = map_fields(parsed, mapping={"SKU": "part_number"})
for row in rows:
    fields = row["fields"]
    provenance = row["provenance"]
    # Hand fields to the existing desk's importer, keeping provenance with its
    # source evidence. This module does not own application schema or fit logic.
```

`ParsedCatalog.source` contains `filename` (basename only), `sha256`, `size_bytes`
and `format`. Each record has its 1-based `record` number, `fields` and `location`:
CSV `line_start`/`line_end`, or JSON `json_pointer`. `map_fields` places these source
and location fields together under each row's `provenance`.

The digest covers the exact original bytes, including BOM and line endings. It is
not a hash of normalized JSON and does not verify supplier legitimacy, price, stock,
compatibility or permission to redistribute catalog content. Errors are surfaced
as `CatalogFileError`; no partial application occurs inside this reader.

## Validation

Executed in the provided cloud container: 19 tests passed in 0.010 seconds. Coverage
includes quoted/multiline CSV, exact source hash/line locations, UTF-8 BOM, leading-zero
identifiers, decimal JSON prices, JSON pointers, duplicate header/key handling,
malformed/ragged/empty files, byte/row limits, explicit mapping collisions, default
preservation, preview generation and existing-output preservation. There were no
supplier operations, real catalog imports, customer transactions or purchases.
