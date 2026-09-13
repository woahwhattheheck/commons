# Agentic GenAI Evaluation Evidence Gate

A deterministic, read-only pre-release evidence control for agentic GenAI systems.

This product compiles a **versioned evaluation portfolio** into one canonical
`RELEASE_CANDIDATE` or `HOLD` receipt. It is designed for teams that need to
show exactly which agent build, evaluation-set generation, rubric, traces,
tool-call observations, automated scores, human decisions, safety results, and
observability evidence supported a release review.

The gate does **not** deploy a model, execute a tool, access customer data, or
make an insurance/financial/compliance decision.

## What it binds

Every compile binds:

- exact evaluation-set ID, generation, digest, and required scenario universe;
- exact agent ID/version/build SHA-256;
- exact rubric ID/generation/digest and minimum score;
- per-scenario category, trace digest, result digest, and observation time;
- automated score and PASS/FAIL result, bound to scenario/trace/result by a canonical automated-evidence digest;
- human-review decision bound back to the exact build, rubric, trace, and result digest;
- safety result bound to the exact build, trace, and result digest;
- observability pointer bound to the exact trace and result digest;
- tool-call ID/tool/action/effect/result and exact trace binding;
- verifier-owned evaluation instant;
- canonical packet SHA-256 and self-verifying receipt SHA-256.

Unknown schema fields, duplicate JSON object keys, Python bool/int aliases, floats where
integer basis points are required, non-canonical timestamps, duplicate IDs, future
evidence, stale evidence, trace/result transplantation, changing file generations,
and receipt drift fail closed.

## Decision semantics

`RELEASE_CANDIDATE` means only that the supplied evaluation evidence satisfies
the declared gate policy at the verifier-owned instant. It is **not** production
release authority.

`HOLD` includes stable reason codes such as:

- `SCENARIO_UNIVERSE_MISMATCH`
- `AGENT_BUILD_MISMATCH`
- `RUBRIC_MISMATCH`
- `TRACE_BINDING_MISMATCH`
- `AUTOMATED_RESULT_BINDING_MISMATCH`
- `RESULT_BINDING_MISMATCH`
- `FUTURE_EVIDENCE`
- `STALE_EVIDENCE`
- `AUTOMATED_SCORE_BELOW_THRESHOLD`
- `AUTOMATED_EVALUATION_FAILED`
- `HUMAN_REVIEW_MISSING` / `HUMAN_REVIEW_FAILED`
- `SAFETY_UNKNOWN` / `SAFETY_FAILED`
- `OBSERVABILITY_INCOMPLETE`
- `TOOL_RESULT_UNKNOWN` / `TOOL_RESULT_FAILED`

Malformed schema is rejected rather than interpreted.

## 180-scenario acceptance portfolio

`golden.py` deterministically generates 180 synthetic scenarios:

- 45 normal;
- 45 tool-using;
- 45 adversarial;
- 45 degraded-observability *challenge cases* whose retained observation evidence
  is still complete.

The clean portfolio compiles to `RELEASE_CANDIDATE`. Any missing required
scenario or a mismatched/stale/unsafe evidence element produces `HOLD`. Two
compiles at the same evaluation instant are byte-identical after canonical JSON
serialization.

The fixture is synthetic. It contains no Caterpillar or other customer data.

## CLI

Compile using the host's current UTC time (there is deliberately no caller
`--as-of` override):

```bash
python -m revenue.agentic_genai_evaluation_gate.cli compile \
  evaluation.json receipt.json --markdown-out receipt.md
```

Verify an existing receipt against the exact packet. Verification first proves the
historical receipt bytes, then re-evaluates freshness at the verifier-owned current
UTC instant; an old receipt whose evidence is now stale returns `CURRENT_EVIDENCE_HOLD`:

```bash
python -m revenue.agentic_genai_evaluation_gate.cli verify \
  evaluation.json receipt.json
```

Input is bounded to 8 MiB, duplicate-key-strict UTF-8/JSON, regular-file only, and
opened with no-follow semantics when the host supports them. The retained descriptor
is read twice with stable identity/size/mtime/ctime and byte equality before semantic
compilation. Output uses create-exclusive publication and never overwrites an existing
artifact.

## Authority ceiling

The receipt always records these authorities as false:

- model deployment;
- tool execution;
- provider mutation;
- customer-data access;
- compliance certification;
- payment;
- external contact;
- revenue recognition.

A buyer can use this as a bounded synthetic/non-production pilot or integrate it
behind its own independently authenticated evaluation-data collection and
release-approval systems. Those upstream/downstream authorities are explicitly
outside this module.
