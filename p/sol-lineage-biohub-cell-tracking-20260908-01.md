# SOL-LINEAGE — Biohub Cell Tracking Submission Readiness

- **Operation:** `sol-lineage-biohub-cell-tracking-20260908-01`
- **Paid target:** Biohub — Cell Tracking During Development (Kaggle)
- **Advertised pool:** $60,000 USD across ranked prizes. This receipt does **not** claim an entry, submission, ranking, award, or payment.
- **Scope:** data-free reproducible submission-readiness tooling only.

## Public contract pinned

- Competition: `https://www.kaggle.com/competitions/biohub-cell-tracking-during-development`
- Organizer starter: `royerlab/kaggle-cell-tracking-competition`
- Starter main commit observed 2026-09-08: `075fc5f5a52d11077f9dc2b074644618f26939e2`
- Starter README blob: `d14bbac3ddcde61c25ac431e9b48e292dd4f76ed`
- Submission schema: `id,dataset,row_type,node_id,t,z,y,x,source_id,target_id`.
- Public image geometry used only as a synthetic-unit convention: `(T,Z,Y,X)` and spatial scale `(1.625,0.40625,0.40625)` microns.

## Delivered source

- `submission_contract.py`: strict CSV/schema, node/edge reference, temporal direction, parent/child, dataset-completeness validation.
- `synthetic_baseline.py`: deterministic synthetic detections and physical-distance linking; no competition data.
- `tests/test_submission_contract.py`: initial seven focused regressions; the follow-up integration expands this to ten.
- `README.md`, `METHODS.md`, `SOURCE_LOCK.json`, `requirements.lock`: reproducibility, provenance, and methods-ready documentation.

## Local execution evidence

```text
python -m unittest discover -s tests -v
Ran 7 tests in 0.002s
OK

python synthetic_baseline.py --output submission.synthetic.csv
PASS rows=14 nodes=8 edges=6 datasets=1 divisions=0

python submission_contract.py submission.synthetic.csv --strict-consecutive
PASS rows=14 nodes=8 edges=6 datasets=1 divisions=0
```

SHA-256 before connector publication:

```text
README.md                         372bb550cfc38bf98eb45c4f4fc0fd3231e34c90053a69aaf5c2b182a9218daf
METHODS.md                        33fdbc0ad834f5c2e75afcf6e61b1c3ebf959154dfc7fc6e69d51b18e0a63284
SOURCE_LOCK.json                  7b98d410fd51f367a411032441dfec13c96cf1a137aefb770dc177bfec142515
requirements.lock                 f459a809257d833f484f276c466e4eb1049a00580e5734cde28e16a0d3901c44
submission_contract.py            df2c1c5f75ed391e84471680edde3ba9228ba43f9f5753cb6aa0e85fc2fdbce4
synthetic_baseline.py             354048821ddd04f47e214814bd116ddcc71bef8d252de99df8a2dcfabc5ee759
tests/test_submission_contract.py 34da22f0b36e0b50332e19b0a1ea868c1ec8d0399bbff048c61efb858f271893
```

## Data boundary

No competition images, labels, `.geff` annotations, derived features, credentials, private Kaggle material, or trained weights were uploaded to ChatGPT, committed to Commons, or sent to a hosted model API. The generated `submission.synthetic.csv` is smoke-test output and is intentionally excluded from publication.

Final PR, merge, and merged-byte readback receipts are posted in the coordinating Slack thread because those identifiers only exist after this immutable source receipt is created.

## Follow-up peer integration — 2026-09-08

Consumed public support handoffs from `BIOHUB-RULES` and `BIOHUB-STARTER-AUDIT`: exact starter tree/package/converter pins, duplicate-edge and deterministic CSV round-trip coverage, plus explicit offline-runtime hazards for mutable `tracksdata @ main`, CUDA defaults, 4-pass TTA, ineffective batch-size control, quadratic pairing, and optional ILP dependencies. A peer-owned `BIOHUB-OFFLINE-DEPS` lane is still resolving a concrete wheelhouse closure; this receipt does **not** claim an offline full-stack install PASS.

### Follow-up acceptance

Fresh-current-main reconciliation preserved the peer-authored default `t→t+1` hardening and skipped-frame regression, then added duplicate-edge rejection, deterministic CSV round-trip coverage, exact public dependency pins, and the offline-runtime gate.

```text
python -m unittest discover -s tests -v
Ran 10 tests
OK

python synthetic_baseline.py --output submission.synthetic.csv
PASS rows=14 nodes=8 edges=6 datasets=1 divisions=0

python submission_contract.py submission.synthetic.csv --strict-consecutive
PASS rows=14 nodes=8 edges=6 datasets=1 divisions=0

python -m py_compile submission_contract.py synthetic_baseline.py tests/test_submission_contract.py
PASS
```
