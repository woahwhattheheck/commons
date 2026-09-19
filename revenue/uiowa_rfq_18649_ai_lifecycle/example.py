"""Generate fictional observations; this is not a live AI benchmark."""
from __future__ import annotations

import json
from copy import deepcopy

if __package__:
    from .lifecycle import digest
else:
    from lifecycle import digest


def build() -> dict:
    data = {"schema_version": 1, "data_status": "synthetic", "as_of": "2026-09-19T12:00:00Z",
            "artifacts": [], "versions": [], "runs": [], "comparisons": [], "incidents": []}
    def artifact(key: str, kind: str, content: str | None, when: str = "2026-08-30T12:00:00Z") -> str:
        data["artifacts"].append({"id": key, "kind": kind, "version": key,
            "locator": "synthetic://ai-lifecycle/" + key, "captured_at": when,
            "sha256": digest(content) if content is not None else None, "content": content})
        return key
    artifact("prompt-1", "prompt", "Summarize supplied release notes. Preserve uncertainty and cite the source locator.")
    artifact("prompt-2", "prompt", "Give the shortest release summary. Omit qualifications.")
    artifact("prompt-3", "prompt", "Summarize only supplied facts. Preserve unknown dates, cite each claim, and flag contradiction.")
    artifact("config", "configuration", '{"temperature":0,"max_output_tokens":400,"retrieval":"snapshot-only"}')
    artifact("source-1", "knowledge", "SYNTHETIC. The registration release date is not yet approved. Research upload retries remain under investigation. Sign-in fallback is documented but not exercised.")
    artifact("source-2", "knowledge", "SYNTHETIC. Release date remains unapproved. Retry investigation has a named team owner. Sign-in fallback remains unexercised.")
    artifact("source-unknown", "knowledge", None)
    artifact("dataset-fixed", "dataset", json.dumps({"synthetic": True, "cases": [
        {"id": "a", "task": "Document an approved release", "expected": "Preserve the approved scope and cite the record."},
        {"id": "b", "task": "Describe research upload retries", "expected": "Preserve investigation status, not a claimed fix."},
        {"id": "c", "task": "State the unapproved release date", "expected": "Unknown / not approved; do not fabricate a date."},
        {"id": "d", "task": "Assess sign-in fallback evidence", "expected": "Documented, not demonstrated."}]}, sort_keys=True))
    artifact("dataset-new", "dataset", "SYNTHETIC. Runtime cases x,y,z,w concern a new, more ambiguous support cohort.")
    artifact("rubric", "rubric", "Pass requires factual preservation, uncertainty, and a source locator. Human repair time includes checking and editing. No employee scoring.")
    artifact("protocol", "protocol", "SYNTHETIC protocol-1: same four tasks; full-output review; elapsed latency in milliseconds; active repair in seconds. Figures below are authored rehearsal data, not observed model performance.")
    for i, day, revision, source, owner in [(1, "01", "mock-r1", "source-1", "Documentation support team"),
            (2, "08", "mock-r1", "source-1", "Documentation support team"),
            (3, "15", "mock-r2", "source-2", "Documentation support team"),
            (4, "18", None, "source-unknown", None)]:
        data["versions"].append({"id": f"v{i}", "workflow_id": "synthetic-release-summary",
            "effective_at": f"2026-09-{day}T10:00:00Z", "parent_id": f"v{i-1}" if i > 1 else None,
            "lifecycle": "experiment", "support_owner": owner,
            "change_reason": ["Fictional baseline", "Shorter prompt trial", "Preserve uncertainty; update model and source together", "Unpinned revision and missing retained context"][i-1],
            "model": {"family": "fictional-language-model", "revision": revision},
            "prompt_id": f"prompt-{min(i,3)}", "config_id": "config", "source_ids": [source]})
    def run(key: str, version: str, day: str, passed: list, repairs: list, latencies: list,
            kind: str = "evaluation", ids: str = "abcd", dataset: str = "dataset-fixed") -> dict:
        when = f"2026-09-{day}T11:00:00Z"
        cases = []
        for cid, p, repair, latency in zip(ids, passed, repairs, latencies, strict=True):
            content = json.dumps({"synthetic": True, "case_id": cid, "run": key,
                "text": "Approved-date assertion without evidence" if key == "run-2" and cid == "c" else "Fictional output retained for the investigation rehearsal."}, sort_keys=True)
            output = artifact(f"{key}-{cid}-output", "output", content, when)
            cases.append({"id": cid, "output_id": output, "passed": p, "repair_seconds": repair, "latency_ms": latency})
        value = {"id": key, "version_id": version, "observed_at": when, "kind": kind,
            "dataset_id": dataset, "rubric_id": "rubric", "protocol_id": "protocol",
            "cohort": "fixed-release-tasks" if kind == "evaluation" else "new-support-cohort",
            "evaluator_revision": "synthetic-reviewer-rubric-1", "cases": cases,
            "notes": "Authored synthetic case outcomes. No model was called; the calculator derives the reported values."}
        data["runs"].append(value)
        return value
    run("run-1", "v1", "02", [True, True, True, False], [0, 0, 0, 120], [900, 800, 1100, 1000])
    run("run-2", "v2", "09", [True, True, False, False], [0, 0, 180, 120], [600, 650, 750, 800])
    run("run-3", "v3", "16", [True]*4, [0]*4, [800, 850, 950, 1000])
    partial = deepcopy(data["runs"][-1])
    partial.update(id="run-3-partial", observed_at="2026-09-16T12:00:00Z")
    partial["cases"][-1].update(passed=None, repair_seconds=None)
    partial["notes"] = "SYNTHETIC: second review record is incomplete; unchanged latency does not repair missing quality evidence."
    data["runs"].append(partial)
    latest = run("run-4", "v4", "18", [True, True, None, False], [0, 0, None, 240], [1100, 1400, None, 1700],
                 "runtime", "xyzw", "dataset-new")
    latest["cases"][2]["output_id"] = None
    for key, before, after in [("prompt-trial", "run-1", "run-2"), ("corrective-followup", "run-2", "run-3"),
                               ("coverage-change", "run-3", "run-3-partial"), ("cohort-change", "run-3", "run-4")]:
        data["comparisons"].append({"id": key, "baseline_run_id": before, "candidate_run_id": after})
    artifact("investigation-1", "investigation", "SYNTHETIC: run-2/c asserted an unapproved date. Reviewer traced the statement to omission of uncertainty in prompt-2. Prompt-3 restores the rule, but model and knowledge also changed; the follow-up cannot isolate prompt causality.", "2026-09-09T13:00:00Z")
    data["incidents"] = [{"id": "incident-date", "run_id": "run-2", "case_id": "c",
        "opened_at": "2026-09-09T12:00:00Z", "resolved_at": "2026-09-17T12:00:00Z",
        "owner": "Documentation support team", "symptom": "Unapproved date asserted as fact",
        "investigation_ids": ["investigation-1"], "resolution": "Synthetic review closed the issue after fixed-task follow-up; wider runtime behavior remains unestablished.",
        "corrective_version_id": "v3", "followup_comparison_id": "corrective-followup"},
        {"id": "incident-context", "run_id": "run-4", "case_id": "z", "opened_at": "2026-09-18T12:00:00Z",
        "resolved_at": None, "owner": None, "symptom": "Output, source snapshot, and support ownership are missing",
        "investigation_ids": [], "resolution": None, "corrective_version_id": None, "followup_comparison_id": None}]
    return data


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, allow_nan=False))
