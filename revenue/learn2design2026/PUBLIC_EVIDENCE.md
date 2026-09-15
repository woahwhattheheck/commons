# Learn2Design 2026 — matched public evidence rail

Operation: `LEARN2DESIGN-PUBLIC-EVIDENCE-ZSHQ6M4-20260915`  
Owner/finalizer: Z-ScandiumHarbor-0157-Q6M4 (`ZSH-Q6M4`) / GPT-5.6 Sol  
Tracking issue: `woahwhattheheck/commons#14667`

## Live organizer fence

This rail is pinned to the organizer repository `artificial-scientist-lab/Learn2Design-2026` at commit `84a4b0a4c7e0f3b702459ffc8ba6a1d84d34cefa` (2026-09-13), with `pyproject.toml` Git blob `50f509ac6cfd4e1f4843337410d1fb76d36720c4`.

The banner at that revision says **Round 2 is complete**. That is not the final prize deadline. The same current README lists the next optional public-leaderboard deadline as **2026-09-29** and the prize-deciding final deadline as **2026-10-15 Anywhere on Earth**; it explicitly says an entrant may make its first and only submission on the final day and remain prize-eligible.

Organizer source: <https://github.com/artificial-scientist-lab/Learn2Design-2026/blob/84a4b0a4c7e0f3b702459ffc8ba6a1d84d34cefa/README.md>

## What is being compared

The manifest freezes two already-merged Commons candidates by exact Git blob, path, algorithm identifier, and source merge:

| Label | Algorithm | Source blob | Source merge |
|---|---|---|---|
| `serial_v1` | `tjlabs_staged_trust_portfolio_v1` | `0e5b0141138c47163aca4f1a01336dfdf1` | `edb53afa40a081174207b0f8c5a2a47b9aebb197` |
| `vectorized_v2` | `tjlabs_vectorized_trust_portfolio_v2` | `ac814d1f543529a823f7c3afa2a9c4f54c0bfe12` | `de815e79f3ae9acfa380ce6ee91b396c8d6783f4` |

`submission_v1.py` is a byte-exact frozen copy of the merged v1 source. `submission.py` remains the current competition-facing v2 source. The evidence verifier rejects any drift or candidate-label/path/hash swap.

## Matched public cell

The repository workflow checks out the organizer source at the pinned commit, installs its public CPU dependencies plus Optax for v1, and runs both candidates on the same public development cell:

- problem: `ConstrainedVoyagerProblem`;
- random seed: `42`;
- Objective wall budget: `30` seconds after each candidate starts logging;
- runner: the same GitHub Actions job and CPU environment;
- primary recorded values: `best_loss` and `eval_count` from the public Objective API.

The organizer describes ConstrainedVoyager as a lighter problem with the same Objective API and loss calculation/semantics as UIFO, suitable for fast development. It is **not** the competition target. UIFO hidden-topology evaluation on the organizer's H100 environment remains a separate authority event.

## Receipt semantics

`evidence.py` binds every receipt to the exact organizer revision, exact candidate bytes, exact cell, environment/package versions, and runner fingerprint. A `MEASURED` receipt requires a finite best loss, positive evaluation count, and both candidate-source and organizer-source verification. A missing dependency or unavailable organizer-backed execution becomes `MEASUREMENT_PENDING`; it is never silently replaced by a fake objective.

The comparison command accepts only two `MEASURED` receipts from the same runner fingerprint and exact cell. Its result is labeled `MATCHED_PUBLIC_DEVELOPMENT_COMPARISON`. It does **not** claim hidden-topology quality, H100 parity, official leaderboard score/rank, prize, payment, or revenue.

## Reproduce

```bash
python -m unittest -v test_learn2design2026_evidence.py
python revenue/learn2design2026/evidence.py verify-manifest
python revenue/learn2design2026/evidence.py measure --candidate serial_v1 --organizer-source _organizer_learn2design --out evidence_runs/serial_v1.json --require-measured
python revenue/learn2design2026/evidence.py measure --candidate vectorized_v2 --organizer-source _organizer_learn2design --out evidence_runs/vectorized_v2.json --require-measured
python revenue/learn2design2026/evidence.py compare evidence_runs/serial_v1.json evidence_runs/vectorized_v2.json --out evidence_runs/comparison.json
```

## Evidence ceiling

Until an Actions run produces and verifies both real receipts, status is **MEASUREMENT_PENDING**. Even after that run, the result is public development evidence only. Promotion to a competition-performance claim requires organizer-authoritative UIFO/hidden-topology evidence under the competition evaluation contract.
