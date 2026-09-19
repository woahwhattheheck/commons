# UIOWA-127 — provenance-preserving local evidence search

A deterministic, offline search component over **already-merged synthetic RFQ 18649 preparation records**. It indexes source metadata, traceability observations, findings, and locator-preserving extracted text without an external model or network service at runtime.

## Provenance contract

Every normalized record carries:

- its stable record ID and record type;
- the exact upstream repository path and Git blob SHA used to prepare the fixture;
- its native source locator;
- the native source reference when one exists (`synthetic://…` for workshare authority records), otherwise the exact GitHub file URL;
- linked IDs for finding → evidence relationships.

The committed fixture manifest pins the upstream blob SHAs. Search never invents a source link or fills a missing record with an answer.

## Corpus used by the worked example

- 12 source-metadata records from `uiowa_rfq_18649_workshare/fixtures/synthetic_authority.json`;
- 8 observation/evidence records from `uiowa_rfq_18649_traceability_rehearsal/evidence.csv`;
- 3 findings from `uiowa_rfq_18649_traceability_rehearsal/findings.csv`;
- 4 locator-preserving segments produced from the merged document-extraction sample text.

Total: **27 records**. All are synthetic preparation artifacts, not University of Iowa findings.

## Ranking

The search is transparent lexical retrieval: Unicode case-folded word tokens; each matched term contributes `idf(term) × (1 + ln(tf))`; an exact normalized query phrase adds 1.0; ties break by stable record ID. No opaque embeddings, personalisation, model inference, or current clock enters ranking.

## Run

```bash
python3 evidence_search.py build fixtures/manifest.json examples/index.json
python3 evidence_search.py query examples/index.json "vulnerability ownership"
python3 evidence_search.py query examples/index.json "end to end propagation"
python3 evidence_search.py query examples/index.json "independent review before merge"
python3 -m unittest -v test_evidence_search.py
python3 -O -m unittest -v test_evidence_search.py
```

See `examples/question-walkthrough.md` for expected reviewer flows and provenance readback.

## Scope boundary

This is navigation over supplied evidence, not an answer generator. A high-ranked hit is not a finding, a confidence score, or proof that an observed practice exists outside the referenced synthetic record. No result means only that the indexed packet did not match the query.
