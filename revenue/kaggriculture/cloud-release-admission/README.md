# TITAN V3 exact-head release admission

This directory contains a **fail-closed, read-only admission compiler** for a fully assembled TITAN candidate. It does not change gameplay policy, run simulations, publish an archive, update canonical pointers, or submit anything to Kaggle. Its only output is a deterministic `ADMIT` or `HOLD` manifest for one externally pinned candidate head.

The compiler closes a release-selection gap exposed during V3 work: an aggregate-positive panel can still be unusable because it belongs to a stale PR head, a second workflow attempt, an incomplete opponent/seed/seat bank, a byte-identical wrapper with different unpinned dependencies, a negative opponent×seat or seed stratum, or an action trace that never changed the realized world.

## What is independently bound

The caller supplies the expected base commit, candidate/PR/workflow head, workflow run ID, source digest, engine digest, evaluator digest, baseline and candidate archive/tree digests, report digest, frozen-bank digest, and policy digest. Those values are not learned from the candidate receipt.

The compiler then verifies all of the following before admission:

- strict UTF-8 JSON with duplicate keys, `NaN`, `Infinity`, booleans-as-numbers, unknown fields, and malformed hashes rejected;
- workflow `status=completed`, `conclusion=success`, `attempt=1`, and exact `run head = PR head = receipt head = expected head`;
- actual baseline archive, candidate archive, report, and policy byte counts and SHA-256 digests;
- exact extracted file sets for both packages, with no symlinks, missing files, extras, or changed bytes;
- a deterministic transitive-tree digest over every package file, rather than a digest of `main.py` alone;
- one and only one result for every frozen opponent × seed × seat cell, with seats exactly `[0, 1]`;
- action-trace and world-trace activity agreement, plus a common preworld, unchanged rival action, changed focal action, and changed postworld at the first divergence;
- own-score, margin, and W/T/L values derived from raw scores, never trusted from labels;
- global, opponent×seat, seed-cluster, and single-cell policy gates; and
- configurable zero-lost-win and zero-new-loss requirements.

A structurally valid candidate that misses any gate returns exit code `1` and a `HOLD` manifest. Malformed, stale, incomplete, or unverifiable input returns exit code `2` and a `HOLD` manifest. Only a complete pass returns exit code `0` and `ADMIT`.

## Usage

```bash
python revenue/kaggriculture/cloud-release-admission/admit_release.py \
  --receipt evidence/receipt.json \
  --policy evidence/policy.json \
  --report evidence/report.json \
  --baseline-root extracted/baseline \
  --candidate-root extracted/candidate \
  --baseline-artifact artifacts/baseline.tar \
  --candidate-artifact artifacts/candidate.tar \
  --expected-base "$BASE_COMMIT" \
  --expected-head "$PR_HEAD_COMMIT" \
  --expected-workflow-run-id "$WORKFLOW_RUN_ID" \
  --expected-source-sha256 "$SOURCE_SHA256" \
  --expected-engine-sha256 "$ENGINE_SHA256" \
  --expected-evaluator-sha256 "$EVALUATOR_SHA256" \
  --expected-baseline-archive-sha256 "$BASELINE_ARCHIVE_SHA256" \
  --expected-baseline-tree-sha256 "$BASELINE_TREE_SHA256" \
  --expected-candidate-archive-sha256 "$CANDIDATE_ARCHIVE_SHA256" \
  --expected-candidate-tree-sha256 "$CANDIDATE_TREE_SHA256" \
  --expected-report-sha256 "$REPORT_SHA256" \
  --expected-bank-sha256 "$BANK_SHA256" \
  --expected-policy-sha256 "$POLICY_SHA256" \
  --output evidence/release-decision.json
```

The output is canonical JSON. `decision_sha256` is the SHA-256 of that canonical document with the `decision_sha256` member removed. Numeric metrics are emitted as exact decimal strings so repeated evaluation of identical inputs is byte-stable.

## Input contract

### Receipt

The receipt has exactly these top-level members:

```text
schema_version, candidate, packages, workflow, bank, policy, report
```

`candidate` binds the candidate name, base/head/PR-head commits, source SHA-256, engine SHA-256, and evaluator SHA-256.

Each package record contains its archive digest and byte count, entrypoint, transitive-tree digest, and a sorted exact manifest of `{path, sha256, bytes}` records. The tree digest is calculated over canonical JSON:

```json
{"schema_version":1,"files":[...]}
```

`workflow` binds the run ID, terminal state, one-shot attempt, head SHA, and all artifact digests and byte counts. `bank` contains sorted opponent package/tree pins, sorted seeds, seats `[0, 1]`, and its canonical digest. `policy` and `report` contain their actual file digests and byte counts.

### Report

The report binds the bank ID, candidate head, both package trees, engine, evaluator, and sorted result cells. Every cell contains raw baseline and candidate own/rival scores, positive trace-step counts, whole-game action/world trace digests, and either `null` or one first-divergence witness. The witness step is zero-based and must lie inside both traces.

An active witness contains:

```text
step
baseline_preworld_sha256, candidate_preworld_sha256
baseline_focal_action_sha256, candidate_focal_action_sha256
baseline_rival_action_sha256, candidate_rival_action_sha256
baseline_postworld_sha256, candidate_postworld_sha256
```

At the claimed first divergence, preworld digests must be equal, rival-action digests must be equal, focal-action digests must differ, and postworld digests must differ.

### Policy

`example_policy.json` is intentionally conservative and is only an example. Production must pin the reviewed policy file by SHA-256 outside the receipt. The receipt cannot weaken its own thresholds because the compiler compares the actual policy bytes to the caller-supplied expected policy digest.

## Test suite

```bash
cd revenue/kaggriculture/cloud-release-admission
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_admit_release.py
```

The 26-case predecessor-killing suite covers:

- exact-head happy path and byte-deterministic output;
- a byte-identical `main.py` wrapper with a real transitive dependency change;
- queued workflow, stale run head, and second attempt;
- global-positive but opponent×seat-negative and seed-negative panels;
- identical transitive trees despite an allegedly active report;
- missing and duplicate grid cells;
- out-of-range first-divergence, action-only/no-world, and score-only/no-causal-change evidence;
- lost wins/new losses derived from scores;
- archive mutation after receipt creation;
- externally mismatched workflow run, comparator tree, report, or policy pin;
- duplicate JSON keys, `NaN`, and booleans in numeric fields;
- unmanifested package files; and
- output/input alias protection.

## Release boundary

`ADMIT` means only that the supplied exact candidate satisfies the supplied exact frozen-bank policy. It is not a promotion action. Canonical archive selection, pointer mutation, provider work, Kaggle upload, and submission remain outside this tool and under the existing release authority.
