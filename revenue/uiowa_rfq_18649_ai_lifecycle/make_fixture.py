#!/usr/bin/env python3
"""Build explicitly authored synthetic observations; this does not simulate model inference."""
from __future__ import annotations
import json
from pathlib import Path
from lifecycle import canonical, sha256


def build() -> dict:
    artifacts = []
    def artifact(key, value, retained=True):
        content = value if isinstance(value, str) else canonical(value)
        artifacts.append({"id": key, "content": content if retained else None, "sha256": sha256(content), "locator": "synthetic://uiowa-079/" + key})
        return key

    artifact("prompt-v1", "Extract the owner and stated deadline. Return a JSON object.")
    artifact("prompt-v2", "Extract owner and deadline. Fill missing values using typical practice.")
    artifact("config", {"seed": 17, "temperature": 0, "note": "Authored synthetic metadata, not an inference execution record."})
    artifact("code", "synthetic-adapter/v1: fixture-only manifest; no model adapter is implemented")
    artifact("environment", {"runtime": "synthetic-runtime/v1", "dependencies": [], "note": "Descriptive synthetic record, not an installed runtime."})
    artifact("source-a", "Release handoff A: release-duty owns the task; complete in 7 days.")
    artifact("source-b", "Release handoff B: service-rotation owns the task; deadline is not stated.")
    artifact("source-c", "Release handoff C: deadline is 2 days; ownership is not stated.")
    artifact("source-a-revised", "Revision 2 of handoff A: release-duty owns the task; complete in 10 days.")
    artifact("source-d", "Handoff D: research-ops owns the task; deadline is 4 days.")
    definitions = [
        ("a", "source-a", {"owner": "release-duty", "deadline_days": 7}),
        ("b", "source-b", {"owner": "service-rotation", "deadline_days": None}),
        ("c", "source-c", {"owner": None, "deadline_days": 2}),
        ("a-revised", "source-a-revised", {"owner": "release-duty", "deadline_days": 10}),
        ("d", "source-d", {"owner": "research-ops", "deadline_days": 4}),
    ]
    cases, expected = [], {}
    for cid, source, answer in definitions:
        inp = artifact("input-" + cid, {"task": "Extract owner and deadline; unsupported values must be null.", "source_id": source})
        exp = artifact("expected-" + cid, answer)
        cases.append({"id": cid, "input_artifact_id": inp, "expected_artifact_id": exp, "source_artifact_ids": [source]})
        expected[cid] = answer
    artifact("investigation-v2", "SYNTHETIC investigation: v2 changes only the prompt text. Its instruction to fill missing values coincides with an additional incorrect owner in case c. Case b remains wrong. Matched-cohort association is observable; this fixture is not a causal model experiment.")
    artifact("investigation-v3", "SYNTHETIC investigation: v3 changes the named synthetic model revision while keeping prompt, cases, inputs and evaluator fixed. Retained outputs now preserve unknowns. The scorer recomputes this difference, but no model has been run.")
    artifact("investigation-v4", "SYNTHETIC investigation: source A was revised and case D added. The model alias lacks an immutable revision; support ownership and D's output were not recorded. A 3/3 scored result is only 3/4 coverage and must not be compared as an overall improvement.")
    artifact("runtime-note", "SYNTHETIC runtime log excerpt: request-1 returned, request-2 errored (SIM-INC-1), request-3 has no known outcome. No measured live latency or real incident is represented.")
    releases = []
    for n in range(1, 5):
        releases.append({
            "id": f"v{n}", "workflow_id": "SYNTHETIC-handoff-extractor", "group": "ESS",
            "created_at": f"2026-09-{n:02d}T09:00:00Z", "parent_id": f"v{n-1}" if n > 1 else None,
            "model": {"name": "synthetic-extractor-not-a-live-model", "revision": "A" if n < 3 else "B" if n == 3 else None, "artifact_id": None},
            "prompt_artifact_id": "prompt-v1" if n == 1 else "prompt-v2", "config_artifact_id": "config", "code_artifact_id": "code", "environment_artifact_id": "environment",
            "dataset_case_ids": ["a", "b", "c"] if n < 4 else ["a-revised", "b", "c", "d"], "evaluator_id": "exact-json-v1",
            "owner_role": "synthetic workflow owner", "support_role": "synthetic service rotation" if n < 4 else None,
            "input_source_ids": ["source-a", "source-b", "source-c"] if n < 4 else ["source-a-revised", "source-b", "source-c", "source-d"],
            "change_reason": ["Initial retained-output baseline.", "Prompt changed to encourage filling missing values.", "Named synthetic model revision changed.", "Source and dataset changed; model revision and support ownership absent."][n-1],
            "investigation_artifact_ids": [f"investigation-v{n}"] if n > 1 else [],
        })
    observations = {"v1": {"a": expected["a"], "b": {"owner": "service-rotation", "deadline_days": 30}, "c": expected["c"]}, "v2": {"a": expected["a"], "b": {"owner": "service-rotation", "deadline_days": 30}, "c": {"owner": "release-duty", "deadline_days": 2}}, "v3": {c: expected[c] for c in ["a", "b", "c"]}, "v4": {c: expected[c] for c in ["a-revised", "b", "c"]}}
    runs = []
    for rid, outputs in observations.items():
        for cid, output in outputs.items():
            oid = artifact(f"output-{rid}-{cid}", output)
            runs.append({"id": f"eval-{rid}-{cid}", "release_id": rid, "case_id": cid, "kind": "evaluation", "occurred_at": f"2026-09-0{rid[-1]}T10:00:00Z", "input_artifact_id": "input-" + cid, "output_artifact_id": oid, "outcome": "success", "latency_ms": None, "incident_id": None})
    runs.append({"id": "eval-v4-d", "release_id": "v4", "case_id": "d", "kind": "evaluation", "occurred_at": "2026-09-04T10:00:00Z", "input_artifact_id": "input-d", "output_artifact_id": None, "outcome": "success", "latency_ms": None, "incident_id": None})
    for i, outcome in enumerate(["success", "error", "unknown"], 1):
        runs.append({"id": f"runtime-v2-{i}", "release_id": "v2", "case_id": "a", "kind": "runtime", "occurred_at": f"2026-09-02T11:0{i}:00Z", "input_artifact_id": "input-a", "output_artifact_id": "output-v2-a" if i == 1 else None, "outcome": outcome, "latency_ms": None, "incident_id": "SIM-INC-1" if i == 2 else None})
    events = [{"id": "baseline", "release_id": "v1", "occurred_at": "2026-09-01T10:30:00Z", "kind": "observation", "artifact_ids": ["output-v1-b"], "summary": "Synthetic baseline: two of three exact-JSON cases pass."}]
    for n in range(2, 5):
        events.append({"id": f"investigate-v{n}", "release_id": f"v{n}", "occurred_at": f"2026-09-0{n}T12:00:00Z", "kind": "investigation", "artifact_ids": [f"investigation-v{n}"], "summary": releases[n-1]["change_reason"]})
    events.append({"id": "runtime-observation", "release_id": "v2", "occurred_at": "2026-09-02T11:30:00Z", "kind": "observation", "artifact_ids": ["runtime-note"], "summary": "One supplied success, one error, one unknown; none is a live operational measurement."})
    return {"schema_version": 1, "synthetic": True, "artifacts": artifacts, "cases": cases, "releases": releases, "runs": runs, "events": events}


if __name__ == "__main__":
    path = Path(__file__).with_name("synthetic-lifecycle.json")
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path.name}; authored fixtures only, no model inference.")
