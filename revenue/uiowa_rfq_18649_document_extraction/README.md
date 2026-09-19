# University of Iowa RFQ 18649 — locator-preserving document extraction

Operation: **UIOWA-032**

This additive tool turns representative PDF, DOCX, and plain-text evidence artifacts into
searchable JSON while preserving a source locator that a report writer can follow back to
the original artifact. It is designed for assessment-production support, not for scoring,
authority, OCR, or University submission.

## What it preserves

- **PDF:** one-based page number plus block number.
- **DOCX:** heading path plus paragraph/table index. DOCX files do not contain reliable
  rendered page numbers, so the adapter does not invent them.
- **TXT/Markdown:** heading path plus one-based line range.
- **Tables:** DOCX tables are emitted separately and linearized row-major with ` | `
  separators, with an explicit warning.
- **Unreadable passages:** empty/image-only PDF pages produce an `unreadable` segment
  and an OCR-required warning instead of silent omission or fabricated text.

Every result also carries the input byte count and SHA-256 so the locator can be tied to
the exact source bytes.

## Install

Python 3.11+ and `pypdf` are required for PDF extraction:

```bash
python -m pip install -r requirements.txt
```

DOCX and plain-text extraction use the standard library.

## Run

```bash
python make_synthetic_corpus.py
python extract.py fixtures/sample.pdf > /tmp/sample-pdf.json
python extract.py fixtures/sample.docx > /tmp/sample-docx.json
python extract.py fixtures/sample.txt > /tmp/sample-text.json
```

The generated corpus is deliberately synthetic and safe for the public repository.

## Output contract

```json
{
  "schema": "uiowa.document-extraction.v1",
  "document": {
    "name": "sample.pdf",
    "type": "pdf",
    "bytes": 0,
    "sha256": "..."
  },
  "status": "ok",
  "warnings": [],
  "segments": [
    {
      "segment_id": "pdf-0001",
      "kind": "page_text",
      "locator": "page 1, block 1",
      "text": "...",
      "heading_path": [],
      "warnings": []
    }
  ]
}
```

`status` is `ok`, `partial`, `unreadable`, or `error`. A caller should retain both the
document SHA-256 and the segment locator when quoting or synthesizing findings.

## Acceptance

```bash
python make_synthetic_corpus.py
python -m unittest -v test_extract.py
python extract.py fixtures/sample.pdf
python extract.py fixtures/sample.docx
python extract.py fixtures/sample.txt
```

Acceptance requires:

1. PDF quotations can be traced to the correct one-based page.
2. DOCX quotations can be traced to a heading path and paragraph/table index.
3. plain text quotations can be traced to exact line ranges.
4. tables are explicit segments rather than flattened invisibly into adjacent prose.
5. image-only/empty PDF pages are flagged as unreadable and OCR-required.
6. the exact source bytes are bound by SHA-256.

## Scope and limits

This adapter performs **text extraction, not OCR**. Scanned/image-only PDFs are therefore
reported as requiring OCR. Complex PDFs can have reading-order limitations in their text
layer; page locators remain valid even when layout reconstruction is imperfect. DOCX page
numbers depend on a rendering engine and are not stable in the OOXML package, so the
portable locator is the document heading path plus paragraph/table index.

The tool does not determine evidence truth, maturity, compliance, acceptance, or
recommendations. It does not contact the University, Clark's Consulting, or any external
provider and does not write private assessment evidence to the repository.
