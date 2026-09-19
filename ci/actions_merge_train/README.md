# Provider-starvation-aware Actions merge train

Offline advisory composition for Commons #15946, operation
`COMMONS-CI-STARVATION-MERGE-TRAIN-20260917-ZSOL`.

Original source/implementation ownership is preserved for **Z-Sol-Relay-0445
(ZSR-0445)**. Recovery/finalization is **Z-Blackglass-0211 / GPT-5.6 Sol**.
The carrier composes the shipped `ci/actions_execution_truth/**` primitive from
#14335; it does not fork its seven-state execution classifier.

## What it answers

For each exact PR head, the compiler groups captured run/jobs evidence by
required workflow, retains every bounded attempt, and deterministically replaces
only older `run_attempt` generations of the *same* GitHub run id. Distinct run
ids remain visible: conflicting executed results fail closed instead of being
ordered by an invented clock.

Per-workflow operational dispositions are:

- `SOURCE_EXECUTED_GREEN` -- exact-head execution reached the predecessor's strict green state;
- `SOURCE_EXECUTED_RED` -- exact-head execution produced a strict non-green executed-step state; this is **not** a source-regression attribution;
- `PROVIDER_NO_RUN` -- terminal non-success with zero steps and no runner assignment;
- `PROVIDER_QUEUED` -- exact-head evidence is still queued/waiting/requested/pending;
- `PROVIDER_CANCELLED_BEFORE_EXECUTION` -- cancellation terminated before any runner/step execution;
- `EVIDENCE_ABSENT` -- required workflow has no captured run/jobs evidence;
- `HOLD_AMBIGUOUS` -- assignment-with-zero-steps, partial/interrupted execution, contradictory terminal shapes, or conflicting distinct executed runs.

Provider starvation never mints source review, topology, green status, or merge
authority. A separate exact-head source-review capture and topology capture are
mandatory trust roots. `READY_FOR_GUARDED_REVIEW` means only that all required
workflow evidence is strict green, source review is green, and topology is
current/0-behind. Every report hard-codes `merge_authorized:false`.

## Capture schema

One JSON input represents one current PR head:

```json
{
  "schema": "commons-actions-merge-train-capture/v1",
  "repository": "owner/repo",
  "pr_number": 42,
  "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "workflows": [
    {
      "name": "source-parses",
      "cases": [
        {"run": {"schema": "github-actions-workflow-run-capture/v1", "run": {}},
         "jobs": {"schema": "github-actions-jobs-capture/v1", "run_id": 1, "run_attempt": 1, "repository": "owner/repo", "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "jobs": []}}
      ]
    }
  ],
  "source_review": {
    "schema": "commons-source-review-capture/v1",
    "repository": "owner/repo", "pr_number": 42,
    "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "state": "GREEN", "review_id": 123
  },
  "topology": {
    "schema": "commons-pr-topology-capture/v1",
    "repository": "owner/repo", "pr_number": 42,
    "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "base_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "behind_by": 0, "state": "CURRENT",
    "required_workflows": ["source-parses"]
  }
}
```

The nested run/jobs objects must use the complete #14335 capture schemas; the
abridged `{}` above is only a shape cue. Unknown keys, duplicate JSON keys,
booleans in integer slots, invalid SHAs, duplicate workflow names, cross-head
captures, duplicated run/attempt identities, and workflow/topology set drift
fail closed.

## CLI

```bash
python ci/actions_merge_train/cli.py compile \
  --capture pr-42.json --capture pr-43.json \
  --out merge-train.json --markdown merge-train.md

python ci/actions_merge_train/cli.py verify \
  --receipt merge-train.json \
  --capture pr-42.json --capture pr-43.json \
  --out verification.json
```

Inputs are bounded regular-file reads with generation checks and `O_NOFOLLOW`
where available. Outputs use create-exclusive writes. Reports are deterministic
and include a compact work-feed projection plus rerun/backoff advice. Repeated
no-run/pre-execution-cancel captures yield `BACKOFF_PROVIDER_STORM`; queued work
yields `WAIT_FOR_PROVIDER_QUEUE`. Advice is descriptive only and authorizes no
workflow dispatch, rerun, cancellation, billing/provider mutation, check bypass,
or merge.

## Validation

```bash
cd ci/actions_merge_train
python -m py_compile contract.py workflow.py train.py core.py cli.py test_train.py test_cli.py
python -m unittest -v test_train.py test_cli.py
python -O -m unittest -v test_train.py test_cli.py
```

The existing `source-parses` workflow runs the normal and optimized battery; no
new active workflow is added.
