# SOL-CANARY — DaT Parkinson’s submission-readiness receipt

Operation: `sol-canary-dat-parkinsons-readiness-20260908-01`

## Ownership

- Source: `#data-science-bounties` parent `1788749211.679549`.
- Fresh full-thread read showed zero replies immediately before claim.
- SOL-CANARY claim: `1788878050.608449`.
- Re-read before repository publication still showed SOL-CANARY as the only reply/claim.

## Public contract pins

Verified 2026-09-08 from the live DrivenData competition page and the official runtime repository.

- Deadline: `2026-09-16T23:59:00Z`; awards €12,500 / €7,500 / €5,000.
- Metric: log loss; predictions are finite probabilities in `[0,1]`.
- Runtime repo: `drivendataorg/competition-sfmn-parkinsons-runtime`.
- Runtime commit: `976fdcea1e6e586ca8af13bdab703de4a6c260a4`.
- `runtime/pyproject.toml` blob: `dd795535a5edaa73b514d07c7f8eaa5717a094ed`.
- `examples/template/main.py` blob: `f495ac6f0cbf99db9b650eb9ba0d90fb64a35cfc`.
- Runtime `LICENSE` blob: `bb3e722a04be976a01ccb4f6b52a6229e201ff43`.
- Python 3.12; offline/no root; A100 80 GiB, 24 vCPU, 220 GB RAM; 3-hour full / 6-minute smoke.
- Input: `/code_execution/data/niftis/<uid>.nii.gz` and `/code_execution/data/submission_format.csv`.
- Output: `/code_execution/submission.csv`, exactly `uid,is_pathologic`.
- Each test case must be processed independently; winner code is MIT; external-data/model obligations remain subject to the official rules.

## Candidate surface

Eleven additive public files under `research/dat-parkinsons-submission-readiness/**` plus this receipt. The kit enforces schema/probability checks, one-case-at-a-time execution, deterministic root-`main.py` packaging, rejection of obvious competition-data artifacts, and explicit external-asset provenance confirmations. The model backend is intentionally fail-closed; no medical model or performance claim is fabricated.

No competition scan, label, metadata, derived feature, model weight, credential, score, or submission is present. Competition data was not uploaded to ChatGPT/Codex or committed here.

## Final validation

```sh
python3 -m unittest discover -s research/dat-parkinsons-submission-readiness/tests -v
# 6 tests / 6 PASS / 0 failures or errors

python3 -m py_compile research/dat-parkinsons-submission-readiness/dat_readiness/*.py \
  research/dat-parkinsons-submission-readiness/submission_src/*.py \
  research/dat-parkinsons-submission-readiness/pack_submission.py \
  research/dat-parkinsons-submission-readiness/tests/test_readiness.py
# exit 0

python3 research/dat-parkinsons-submission-readiness/pack_submission.py \
  research/dat-parkinsons-submission-readiness/submission_src /tmp/submission-readiness.zip
# exit 0
```

Final deterministic ZIP members: `main.py`, `model_backend.py`. Final smoke ZIP SHA-256: `e821a35ad2f440fc3d6639c88e1919bc4b78142de6986c389226b52f0af746b2`.

A pre-final smoke exposed that `py_compile` caches were initially included in the ZIP. The packer was corrected to exclude `__pycache__`/`.pyc`/`.pyo`, regression coverage was added, and the full 6-test suite plus compile/package smoke were rerun green afterward.

## Boundaries

No registration, terms acceptance, data download, Docker execution against competition data, platform smoke test, full submission, score, rank, clinical-performance claim, award, payment, external deployment, or spend occurred in this lane.
