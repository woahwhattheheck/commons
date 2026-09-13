# CAS actuarial LLM perception benchmark — executable proposal demonstrator

Issue: `#13945`  
Operation: `CAS-ACTUARIAL-LLM-BENCHMARK-ZHR-C8Q6-20260913`

This folder is a **technical demonstrator**, not a claim of actuarial credentials and not a production benchmark. It exists to prove the repeatability, provenance, scoring, and maintenance architecture proposed for the Casualty Actuarial Society's 2026 paid research RFP, *Evaluating LLMs for Actuarial Perception Tasks for an LLM Benchmark and Re-Evaluation Suite*.

Official RFP: https://www.casact.org/2026-ai-rfp

## What is real here

The code implements a provider-neutral, dependency-free scoring contract for objective perception/classification tasks:

- fixed, versioned benchmark JSON;
- exact benchmark SHA-256 binding so results cannot silently float across changed task bytes;
- strict one-prediction-per-task validation;
- exact label-universe and probability validation;
- accuracy, macro-F1, multiclass Brier score, and log loss;
- per-category results;
- deterministic JSON result receipts; and
- a static comparison-page renderer that refuses to mix results from different benchmark digests.

The included eight tasks are **project-authored synthetic software fixtures** dedicated to CC0-1.0. They contain no real claims or policyholder records, are not actuarial advice, and must not be represented as the actuarial benchmark CAS would ultimately approve.

## Why the architecture matches the RFP

CAS asks for a fixed, versioned suite of actuarially relevant perception/classification tasks, legally publishable datasets, objective metrics, repeatable evaluation of commercial and open models, an extensible comparison platform, replication documentation, and a maintenance path that CAS can operate independently.

This demonstrator tests the infrastructure invariants before domain content is introduced. A production project would add an actuarial-SME-controlled item-design and validation workflow, legally reviewed source datasets/simulations, model adapters, run-cost telemetry, richer uncertainty analysis, and a public comparison UI while retaining the exact-result-binding contract shown here.

## Run it

From this directory:

```bash
python -m unittest -v test_benchmark.py
python benchmark.py fixtures/synthetic_tasks.json fixtures/example_predictions.json --model-id fixture-model --output fixture-result.json
python render_report.py fixture-result.json --output fixture-report.html
```

No network calls or API keys are required for the demonstrator.

## Production data boundary

A production task may enter the benchmark only if all of the following are recorded before model scoring:

1. provenance and publication rights are explicit;
2. the ground-truth label has an actuarial validation owner;
3. the task is an objectively scoreable perception/classification item;
4. the task identifier and label universe are stable;
5. the benchmark version is frozen and hashed; and
6. every model result binds that exact digest.

Private claims, personally identifiable records, proprietary carrier documents, or data without downstream publication rights are outside this demonstrator and must not be smuggled into a public CAS suite.

## Proposed handoff shape

The benchmark runner and result schema should remain deliberately boring: JSON in, JSON out, deterministic hashes, stdlib-compatible core. Provider-specific adapters should be separate so OpenAI/Anthropic/Google/open-weight model churn cannot alter benchmark semantics. CAS should be able to replace an adapter, add a model, and re-run a frozen suite without changing the scorer.

See `PROPOSAL_DRAFT.md` for the commercial/research carrier. It intentionally leaves any actuarial SME identity and final compensation split unresolved until a real collaborator accepts.
