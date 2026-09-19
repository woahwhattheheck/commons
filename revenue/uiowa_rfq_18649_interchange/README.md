# UIOWA-096 — interoperable evidence/report handoffs

Isolated kit under `revenue/uiowa_rfq_18649_interchange/`.

Typed JSON-Pointer transport for synthetic assessment envelopes. Whole existing
JSON objects are retained. Assessment and authority fields are not translated
or elevated.

## Formats

| Format | Round trip | Limitation |
| --- | --- | --- |
| JSON | exact Python JSON types | duplicate keys collapse as `json` does |
| CSV | meaning-preserving typed rows | values are serialized; types live in the `type` column |
| XLSX | same row contract | minimal OOXML writer; not Excel-formula evaluation |
| DOCX | reader projection only | paragraph text; page layout unknown |
| PDF | reader projection only | no OCR; text marked unknown without a parser |

Missing vs empty vs null is preserved on JSON/CSV/XLSX via `presence`.

## Commands

```bash
python cli.py json-to-csv examples/synthetic_envelope.json /tmp/out.csv
python cli.py csv-to-json /tmp/out.csv /tmp/back.json
python cli.py json-to-xlsx examples/synthetic_envelope.json /tmp/out.xlsx
python -m unittest -v test_transport.py
```

## Scope

No University records, live provider calls, scheduling, or occupied
workbench/compiler edits.
