# Lost in Transcription — all-three multitrack V2

This additive carrier composes the three already-existing Lost in Transcription workstreams without rewriting them. It is a shared offline ensemble, experiment, package-verification, and readiness layer for `sp-en`, `sp-nh`, and `id-jv`.

## What is new

- One Unicode-preserving normalization + WER implementation across all tracks.
- Deterministic N-best minimum-risk consensus using rank/reliability weights, optional per-track priors, and explicit confidence/ABSTAIN diagnostics.
- Priors are admissible only from `public`, `authorized_local`, or checked-in `synthetic` transcript evidence. No competition transcript/audio bytes belong in git.
- One deterministic experiment schema reports top-1 vs consensus WER separately by track.
- Reproducible ZIP compiler + verifier, static Python import/literal scan for network/secret hazards, offline-runtime check, exact file hashes, and a configurable byte ceiling.
- Bounded local subprocess profiler records wall time, RSS ceiling, return code, and stdout/stderr hashes without retaining output contents; this is execution evidence only when run against the actual prepared local bundle.
- Three-receipt aggregator says only `ALL_THREE_LOCAL_BUNDLES_STRUCTURALLY_READY` when each distinct track has a valid local bundle on the same pinned runtime. It always records `provider_submission=false`, `competition_terms_accepted=false`, `score_claimed=false`, and `prize_claimed=false`.

## Runtime authority

Pinned from the current Commons Spanish-English carrier: `drivendataorg/lost-in-transcription-runtime@c23d3d9942fea1d4d3e4325f6c0f2fe4d74273f6`, Python 3.12, root `main.py`, offline execution, input `/code_execution/data/submission_format.csv`, clips `/code_execution/data/clips`, output `/code_execution/submission/submission.csv`.

## Local evidence flow

```bash
python priors.py fixtures/prior_evidence.jsonl /tmp/priors.json
python experiment.py fixtures/experiment.jsonl /tmp/report.json --priors /tmp/priors.json
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
```

For a real local-runtime bundle, copy `submission_main.py` to `main.py`, copy `model_config.example.json` to `model_config.json` and bind it to the correct track/local model paths, include local model/prior assets, then run `pack.py`. The tool does **not** fetch models or data.

## Claim ceiling

This repository provides offline engineering evidence only. It does not register for a competition, accept terms, upload submissions, call a hosted model/API, establish a leaderboard score/rank, or establish prize/payment/revenue. `ALL_THREE_LOCAL_BUNDLES_STRUCTURALLY_READY` is not a model-execution or provider-submission state.
