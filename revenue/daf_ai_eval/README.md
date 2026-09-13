# DAF26TZ06-NV006 — AI Performance Evaluation Proof

Operation: `DAF26TZ06-NV006-AI-EVAL-PROOF-ZMAT7N5-20260913`

This is a **synthetic/offline technical proof**, not a proposal, procurement response, government simulator integration, or operational decision system.

## Technical seam

The current Air Force STTR topic asks for standardized/adaptive AI performance evaluation in test-and-evaluation settings. Public topic Q&A says Phase I will not provide government AFSIM/TETK access, so this carrier proves a portable contract independent of any government simulator:

`research/synthetic simulator -> adapter record -> strict scenario set -> deterministic metrics -> policy reasons -> canonical receipt`

The adapter record must state `synthetic_or_research_owned=true` and `claims_government_simulator_access=false`; contrary claims fail closed.

Each already-observed scenario binds opaque scenario/family IDs, `BASELINE|PERTURBATION|DRIFT`, expected/observed labels, completion, integer latency, bounded explanation-factor IDs, and explanation SHA-256. Perturbation/drift families require a baseline. Duplicate keys/IDs, unknown fields, unsafe numerics, future/noncanonical time, malformed digests, and unsupported provider claims fail closed.

Metrics are deterministic integers/basis points: accuracy, completion reliability, paired perturbation robustness, baseline-to-drift accuracy drop, explanation-evidence coverage, and nearest-rank p95 latency. A strict policy emits `PROOF_PASS` or `HOLD` with stable reason codes. The report hashes exact scenario, policy, adapter, and report-core bytes; verification exactly recompiles.

No output asserts military suitability, deployment authority, safety certification, mission effectiveness, procurement compliance, sponsor acceptance, award, payment, or revenue.

## Repro

```bash
python -m unittest -v test_evaluator.py
python -O -m unittest -v test_evaluator.py
python -m py_compile evaluator.py cli.py test_evaluator.py
python cli.py compile --scenarios synthetic/scenarios.json --policy synthetic/policy.json --adapter synthetic/adapter.json --report /tmp/daf-ai-eval-report.json --trusted-now 2026-09-13T15:00:00Z
python cli.py verify --scenarios synthetic/scenarios.json --policy synthetic/policy.json --adapter synthetic/adapter.json --report /tmp/daf-ai-eval-report.json --trusted-now 2026-09-13T15:00:00Z
```

## Source / eligibility ledger

Official topic pointer: `https://www.dodsbirsttr.mil/topics-app/?topicId=587b8cc9c0aa47f88bbdd886d4786b67_86660`.

Current public topic records show pre-release 2026-09-02, open 2026-09-23, close 2026-10-21, and Q&A clarifying no government AFSIM/TETK access in Phase I. The exact official Release-6 instructions must be reacquired and hash-bound before any proposal claim.

**Secondary-only until rebound to official instructions:** current program summaries report a Phase-I STTR maximum up to $300,000 / six months and one research-institution partner with minimum small-business/research-institution work shares. These are planning leads, not proposal facts here.

## Research-institution handoff

The partner seam is substantive: a research institution owns/lawfully controls a synthetic or research simulation source and produces adapter-compliant observations/method evidence; TJLabs supplies deterministic evaluation, hostile scenario design, provenance receipts, threshold analysis, and reproducibility tooling; both jointly define Phase-I validation hypotheses/falsifiers. Exact eligibility/work-share/IP/data-rights rules must come from the official solicitation.

No eligible, willing research institution with a substantive work package => `NO PRIME PATH`. Do not invent eligibility or partner consent.
