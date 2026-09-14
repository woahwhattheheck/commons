# Strict held-out validation

The original `acqatlas.py validate` baseline refits TF-IDF on the full corpus for every leave-one-out row. It excludes the held-out document's **label** from recommendation evidence, but the held-out document still contributes vocabulary/document-frequency statistics to the fitted TF-IDF space. That makes the published baseline validation transductive rather than a clean held-out estimate.

For competition evidence, use the additive strict validator:

```bash
python tools/validate_strict.py fixtures/synthetic_procurements.jsonl --top-k 5
```

`strict-held-out-idf-v1` enforces this fold boundary:

1. remove the held-out target from the fit set;
2. fit TF-IDF only on the remaining documents;
3. project the held-out query into that frozen training-fold IDF space;
4. score it against training documents only;
5. record the exact fit-document manifest SHA-256 for every validation row.

The query text is still used for scoring, as it must be at inference time. What it may not do is change the feature-space statistics that were fitted from training data.

## Evidence boundary

- Historical synthetic receipts remain historical artifacts and are not rewritten.
- New competition-facing validation evidence should use the strict validator or a stronger sponsor-approved split.
- Synthetic fixture accuracy is not sponsor accuracy.
- Do not claim GFI validation until the sponsor has authorized access and the run occurs in the permitted private environment.
- This change does not alter clustering or production recommendation behavior; it only supplies a leakage-free validation path.
