# CAS actuarial LLM benchmark reproducibility core

This package is a **buyer-neutral technical evidence package**, not a CAS proposal,
actuarial opinion, benchmark result, contract, or claim of award/revenue. It turns
a fully specified benchmark manifest plus offline model-output records into a
deterministic, content-addressed comparison snapshot.

It was built against the public 2026 Casualty Actuarial Society RFP for an LLM
actuarial perception-task benchmark. That RFP calls for fixed/versioned tasks,
legally usable and publishable data, objective metrics, standardized re-testing of
current commercial and open models, a maintainable comparison platform, public
GitHub publication, replication documentation, and long-term governance.

## What this proves

The core demonstrates the reproducibility/evaluation-engineering boundary that a
qualified actuarial research team can populate with valid task content:

- task identity and version are immutable inputs;
- every dataset and split is SHA-256 bound;
- dataset evidence must explicitly state `confirmed_publishable`, retain an HTTPS
  source/provenance locator, publication/license reference, and provenance;
- the model roster must include provider families `openai`, `anthropic`, and
  `google`, plus at least three distinct open models;
- every model artifact/version is SHA-256 bound;
- every model × task cell must exist exactly once;
- run records bind task version, dataset, split, model artifact, and evaluation
  protocol before scoring;
- binary and multiclass outputs receive objective accuracy, macro-F1, Brier score,
  and log-loss calculations;
- probability vectors must cover exactly the task labels and sum exactly to one;
- the complete comparison snapshot is canonicalized and content-addressed for
  replay/tamper verification;
- governance forbids silent benchmark mutation and reserves actuarial task validity
  to a `qualified_actuarial_reviewer`;
- package output is explicitly `PROPOSAL_TECHNICAL_EVIDENCE_READY`, not CAS
  submission/acceptance, contract, payment, recognized revenue, or actuarial
  authority.

The repository fixture is **synthetic only**. It does not contain insurer,
policyholder, claimant, or production data and it does not call any model/API.

## Acceptance

```bash
python -m unittest revenue.cas_actuarial_llm_benchmark.test_core -v
python -O -m unittest revenue.cas_actuarial_llm_benchmark.test_core -v
python -m py_compile \
  revenue/cas_actuarial_llm_benchmark/core.py \
  revenue/cas_actuarial_llm_benchmark/fixture.py \
  revenue/cas_actuarial_llm_benchmark/cli.py
python -m revenue.cas_actuarial_llm_benchmark.cli fixture \
  --output /tmp/cas-benchmark-snapshot.json
python -m revenue.cas_actuarial_llm_benchmark.cli verify \
  /tmp/cas-benchmark-snapshot.json
```

Expected fixture shape:

- `status=PROPOSAL_TECHNICAL_EVIDENCE_READY`
- 2 versioned synthetic tasks
- 6 synthetic model identities: 3 commercial provider families + 3 open models
- 12 complete model × task runs
- deterministic `snapshot_sha256`
- offline verification returns `snapshot_valid=true`

## Integration boundary

A real CAS research delivery still requires qualified actuarial researchers to
author/approve the benchmark tasks, choose or simulate legally publishable data,
justify task validity and class definitions, identify actual current models and
provider terms, execute model calls under approved budgets, interpret limitations,
write the research report, build/operate the public UI, and satisfy CAS publication,
paper, presentation, governance, and contractual requirements.

This package intentionally does **not** contact CAS, submit a proposal, negotiate
price, call commercial/open model providers, fetch datasets, or assert that the
synthetic fixture measures actuarial competence.
