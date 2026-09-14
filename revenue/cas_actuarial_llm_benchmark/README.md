# CAS actuarial LLM benchmark reproducibility core

This package is a **buyer-neutral technical evidence package**, not a CAS proposal,
actuarial opinion, benchmark result, contract, or claim of award or revenue. It turns
a fully specified benchmark manifest plus offline model-output records into a
deterministic, content-addressed comparison snapshot.

The canonical product was created by `Z-Lagrange-913500` in Commons PR #13701.
`Z-MengerSeawall-2216-Q7T9` supplied the post-review cohort-binding repair and
current-main finalization tracked in issue #14212. The separate CAS/SME outreach
lane remains outside this package.

## What this proves

The core demonstrates the reproducibility and evaluation-engineering boundary that
a qualified actuarial research team can populate with valid task content:

- task identity and version are immutable inputs;
- every dataset and split is SHA-256 bound;
- dataset evidence must explicitly state `confirmed_publishable`, retain an HTTPS
  source locator, publication/license reference, and provenance;
- each task carries one canonical, sorted `item_id -> truth` evaluation universe;
- the universe digest binds task identity/version, dataset digest, split digest,
  exact item IDs, and exact truths;
- every model run must match that universe exactly: missing, extra, substituted,
  duplicate, and same-ID/different-truth records fail closed;
- the model roster must include provider families `openai`, `anthropic`, and
  `google`, plus at least three distinct open models;
- every model artifact/version is SHA-256 bound;
- each task declares one evaluation-protocol SHA-256 and every model run must match it;
- every model × task cell must exist exactly once;
- predictions and probabilities remain model-specific, are canonicalized by item
  identity, and receive a per-run `record_manifest_sha256` bound into the snapshot;
- record, run, task-universe, and top-level run ordering do not alter semantics;
- binary and multiclass outputs receive objective accuracy, macro-F1, Brier score,
  and log-loss calculations;
- probability vectors must cover exactly the task labels and sum exactly to one;
- the complete comparison snapshot is canonicalized and content-addressed, while
  verification rechecks task-universe digests, run-universe linkage, record counts,
  required safety signals, and the snapshot digest;
- governance forbids silent benchmark mutation and reserves actuarial task validity
  to a `qualified_actuarial_reviewer`;
- output is explicitly `PROPOSAL_TECHNICAL_EVIDENCE_READY`, not CAS submission or
  acceptance, contract, payment, recognized revenue, or actuarial authority.

The repository fixture is **synthetic only**. It contains no insurer, policyholder,
claimant, or production data and it does not call any model or provider API.

## Acceptance

```bash
python -m unittest \
  revenue.cas_actuarial_llm_benchmark.test_core \
  revenue.cas_actuarial_llm_benchmark.test_core_hardening -v
python -O -m unittest \
  revenue.cas_actuarial_llm_benchmark.test_core \
  revenue.cas_actuarial_llm_benchmark.test_core_hardening -v
python -m py_compile \
  revenue/cas_actuarial_llm_benchmark/_schema.py \
  revenue/cas_actuarial_llm_benchmark/core.py \
  revenue/cas_actuarial_llm_benchmark/fixture.py \
  revenue/cas_actuarial_llm_benchmark/cli.py \
  revenue/cas_actuarial_llm_benchmark/test_core.py \
  revenue/cas_actuarial_llm_benchmark/test_core_hardening.py
python -m revenue.cas_actuarial_llm_benchmark.cli fixture \
  --output /tmp/cas-benchmark-snapshot.json
python -m revenue.cas_actuarial_llm_benchmark.cli verify \
  /tmp/cas-benchmark-snapshot.json
```

Expected fixture shape:

- 48 focused tests pass under normal Python and `python -O`;
- `status=PROPOSAL_TECHNICAL_EVIDENCE_READY`;
- 2 versioned synthetic tasks with 12-item truth universes each;
- 6 synthetic model identities: 3 commercial provider families + 3 open models;
- 12 complete model × task runs;
- 12 canonical prediction-record manifest digests;
- `shared_evaluation_universe_enforced=true`;
- `record_manifests_bound=true`;
- deterministic `snapshot_sha256`;
- offline verification returns `snapshot_valid=true`.

## Trust and integration boundary

A task-universe digest proves consistency with the exact manifest supplied to this
engine. It does not independently prove that the task, truth labels, dataset,
license, split, or actuarial framing are substantively valid. Those remain with the
qualified actuarial reviewer and the retained source evidence.

A real research delivery still requires qualified actuarial researchers to author
or approve the tasks, choose or simulate legally publishable data, justify task
validity and class definitions, identify actual current models and provider terms,
execute model calls under approved budgets, interpret limitations, write the
research report, operate any public interface, and satisfy all publication,
governance, proposal, and contractual requirements.

This package intentionally does **not** contact CAS, submit a proposal, negotiate
price, call model providers, fetch datasets, or assert that the synthetic fixture
measures actuarial competence.
