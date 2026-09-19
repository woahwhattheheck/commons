#!/usr/bin/env python3
"""Emit deterministic synthetic recovery challenges; no University observations.

The initial corpus binds the R63F donor record shape. A canonical carrier adapter
must translate these records without manufacturing missing evidence. See README.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from runner import SCHEMA, validate_suite

COMMON = ("failure_recognition", "decision_ownership", "recovery_communications")
BASE = {
    "rollback": ("previous_state_available", "rollback_rehearsal", "dependency_compatibility", "side_effect_handling"),
    "forward_repair": ("repair_validated", "deployment_rehearsal", "dependency_compatibility", "side_effect_handling"),
}
DATA = {
    "rollback": ("old_version_compatible", "new_writes_preserved", "migration_reversal_rehearsal"),
    "forward_repair": ("migration_compatibility", "new_writes_preserved"),
}
RECOVERED = "recovery_demonstrated_in_records"
INCOMPLETE = "recovery_not_fully_verified"


def evidence(packet: dict, check: str, option: dict | None, at: str, *, outcome: str = "supports") -> dict:
    identity = (option["id"] + "/" if option else "common/") + check
    return {"id": identity, "check": check, "option_id": option["id"] if option else None,
            "kind": "demonstration", "outcome": outcome, "service": packet["service"],
            "release_version": packet["change"]["to_version"],
            "target_version": option["target_version"] if option else None,
            "observed_at": at, "locator": "fictional://r63f/" + identity,
            "summary": "Synthetic exercise observation for " + check.replace("_", " "),
            "run_id": "SYNTHETIC-R63F-01", "environment": "fictional-representative-rehearsal",
            "representative": True}


def baseline(migration: bool = False) -> dict:
    packet = {"schema_version": 1, "scenario_id": "SYN-MIGRATION-063" if migration else "SYN-CONFIG-063",
              "title": "Fictional schema migration" if migration else "Fictional reversible configuration release",
              "group": "RIS (fictional)" if migration else "ESS (fictional)",
              "service": "Fictional grant milestones" if migration else "Fictional course notices",
              "classification": "synthetic", "as_of": "2026-09-01T10:00:00Z", "evidence_max_age_days": 30,
              "change": {"kind": "data_migration" if migration else "configuration", "from_version": "v17",
                         "to_version": "v18", "deployed_at": "2026-09-01T09:00:00Z"},
              "targets": {"recovery_minutes": 45, "data_loss_minutes": 0, "observation_minutes": 15},
              "timeline": {"impact_at": "2026-09-01T09:00:00Z", "detected_at": "2026-09-01T09:03:00Z",
                           "decided_at": "2026-09-01T09:08:00Z", "action_started_at": "2026-09-01T09:10:00Z",
                           "action_completed_at": "2026-09-01T09:15:00Z"},
              "decision": {"selected_option_id": "repair" if migration else "revert", "owner_role": "Fictional service lead",
                           "rationale": "Preserve schema-compatible writes" if migration else "Restore the demonstrated configuration"},
              "options": [
                  {"id": "revert", "strategy": "rollback", "target_version": "v17", "estimated_action_minutes": [5, 10],
                   "estimated_data_loss_minutes": 0, "rationale": "Compare rollback evidence before choosing"},
                  {"id": "repair", "strategy": "forward_repair", "target_version": "v19", "estimated_action_minutes": [20, 40],
                   "estimated_data_loss_minutes": 0, "rationale": "Compatible forward repair; estimate may exceed objective"}],
              "evidence": [], "recovery": {"checks": [], "observation_minutes": 15, "data_loss_minutes": 0}}
    for check in COMMON:
        packet["evidence"].append(evidence(packet, check, None, "2026-09-01T09:08:00Z"))
    for option in packet["options"]:
        for check in BASE[option["strategy"]] + (DATA[option["strategy"]] if migration else ()):
            outcome = "contradicts" if migration and check == "old_version_compatible" else "supports"
            packet["evidence"].append(evidence(packet, check, option, "2026-09-01T08:30:00Z", outcome=outcome))
    selected = packet["options"][1 if migration else 0]
    domains = ["service", "version", "dependencies", "monitoring"] + (["data_integrity"] if migration else []) + ["data_loss"]
    for domain in domains:
        item = evidence(packet, "verification_" + domain, selected, "2026-09-01T09:30:00Z")
        packet["evidence"].append(item)
        packet["recovery"]["checks"].append({"id": "verify-" + domain, "domain": domain, "result": "pass",
                                              "observed_at": "2026-09-01T09:30:00Z", "evidence_ids": [item["id"]],
                                              "note": "Fictional observed " + domain.replace("_", " ") + " verification"})
    return packet


def replace(path: str, value: Any) -> dict:
    return {"op": "replace", "path": path, "value": value}


def eq(path: str, value: Any) -> dict:
    return {"path": path, "op": "equals", "value": value}


def make_suite() -> dict:
    config, migration = baseline(), baseline(True)
    suite = {"schema": SCHEMA, "title": "R63F recovery evidence and chronology challenges",
             "classification": "synthetic", "baselines": {"configuration": config, "migration": migration}, "cases": []}

    def case(cid: str, purpose: str, edits: list, checks: list | None = None, *, base: str = "configuration", positive: bool = False) -> None:
        suite["cases"].append({"id": cid, "purpose": purpose, "baseline": base, "edits": edits,
                               "positive_control": positive,
                               "expected": {"kind": "return" if checks is not None else "reject", "checks": checks or []}})

    case("CFG-OK", "A complete successful case prevents an always-unknown assessor passing vacuously.", [],
         [eq("/recovery/state", RECOVERED), eq("/recovery/impact_to_verified_minutes", 30.0),
          eq("/options/0/evidence_state", "demonstrated_in_records"), eq("/recovery/data_loss_target", "within")], positive=True)
    case("MIG-OK", "Successful forward recovery is separate from contraindicated rollback and a pessimistic estimate.", [],
         [eq("/recovery/state", RECOVERED), eq("/options/0/evidence_state", "contradicted"),
          eq("/options/1/evidence_state", "demonstrated_in_records"), eq("/options/1/time_target_using_upper_bound", "exceeds")], base="migration", positive=True)
    rehearsal = next(i for i, e in enumerate(config["evidence"]) if e["check"] == "rollback_rehearsal")
    service = next(i for i, e in enumerate(config["evidence"]) if e["check"] == "verification_service")
    rp = f"/evidence/{rehearsal}"
    sp = f"/evidence/{service}"
    variants = [
        ("WRITTEN", "A document does not become a demonstrated rollback.", "kind", "document", "documented_only"),
        ("REPORTED", "An interview is reported practice, not a rehearsal.", "kind", "interview", "reported_only"),
        ("UNDATED", "Undated support cannot establish current practice.", "observed_at", None, "unknown"),
        ("STALE", "Expired demonstration remains visible but not current proof.", "observed_at", "2026-06-01T08:30:00Z", "unknown"),
        ("AGE-BOUNDARY", "Exactly-at-window evidence remains eligible.", "observed_at", "2026-08-02T10:00:00Z", "demonstrated_in_records"),
        ("WRONG-RELEASE", "A different released version cannot prove this release path.", "release_version", "v16", "unknown"),
        ("WRONG-TARGET", "Proof for a different rollback target cannot be borrowed.", "target_version", "v16", "unknown"),
        ("WRONG-SERVICE", "Another service's rehearsal does not establish this service's path.", "service", "Fictional unrelated service", "unknown"),
        ("NO-RUN", "A demonstration needs a run identity.", "run_id", None, "unknown"),
        ("NO-ENVIRONMENT", "A demonstration needs execution context.", "environment", None, "unknown"),
        ("NONREPRESENTATIVE", "Nonrepresentative exercise evidence is not silently promoted.", "representative", False, "unknown"),
    ]
    for name, purpose, field, value, state in variants:
        case("CFG-" + name, purpose, [replace(rp + "/" + field, value)], [eq("/options/0/evidence_state", state)])
    contrary = copy.deepcopy(config["evidence"][rehearsal])
    contrary.update(id="revert/contrary-rehearsal", outcome="contradicts")
    case("CFG-CONFLICT", "Current contrary evidence cannot be outvoted by support.", [{"op": "append", "path": "/evidence", "value": contrary}],
         [eq("/options/0/evidence_state", "conflicting")])
    case("CFG-PRE-ACTION", "Pre-action observations cannot verify a completed recovery.", [replace(sp + "/observed_at", "2026-09-01T09:14:00Z")], [eq("/recovery/state", INCOMPLETE)])
    case("CFG-WRONG-VERIFICATION", "Wrong-release verification does not prove recovery.", [replace(sp + "/release_version", "v16")], [eq("/recovery/state", INCOMPLETE)])
    case("CFG-INFLATED-WINDOW", "A claimed observation window cannot exceed elapsed observation time.", [replace("/recovery/observation_minutes", 20)], [eq("/recovery/state", INCOMPLETE)])
    case("CFG-SHORT-WINDOW", "A short healthy observation cannot satisfy a longer target.", [replace("/recovery/observation_minutes", 5)], [eq("/recovery/state", INCOMPLETE)])
    case("CFG-MISSING-SERVICE", "Missing user-service verification cannot be supplied by infrastructure checks.", [{"op": "remove", "path": "/recovery/checks/0"}], [eq("/recovery/state", INCOMPLETE)])
    reported_fail = copy.deepcopy(config["recovery"]["checks"][0])
    reported_fail.update(id="reported-service-failure", result="fail", evidence_ids=[], note="Fictional unresolved contrary observation")
    case("CFG-REPORTED-FAILURE", "A recorded failure must remain unresolved, even without execution evidence.", [{"op": "append", "path": "/recovery/checks", "value": reported_fail}],
         [eq("/recovery/state", "verification_failure_recorded")])
    contradiction = copy.deepcopy(config["evidence"][service])
    contradiction.update(id="revert/contradictory-service", outcome="contradicts")
    case("CFG-VERIFICATION-CONFLICT", "Conflicting referenced post-action observations invalidate a pass.",
         [{"op": "append", "path": "/evidence", "value": contradiction},
          {"op": "append", "path": "/recovery/checks/0/evidence_ids", "value": contradiction["id"]}], [eq("/recovery/state", INCOMPLETE)])
    case("MIG-MISSING-INTEGRITY", "A migration restart does not establish reconciled business data.", [{"op": "remove", "path": "/recovery/checks/4"}], [eq("/recovery/state", INCOMPLETE)], base="migration")
    case("MIG-LOSS-UNKNOWN", "Unknown loss is not zero, even when service recovery is demonstrated.", [replace("/recovery/data_loss_minutes", None)],
         [eq("/recovery/state", RECOVERED), eq("/recovery/data_loss_target", "unknown")], base="migration")
    case("CFG-OBJECTIVE-UNKNOWN", "An absent recovery objective cannot produce an objective pass.", [replace("/targets/recovery_minutes", None)],
         [eq("/recovery/recovery_target", "unknown"), eq("/recovery/state", RECOVERED)])
    case("CFG-DECISION-TIME-UNKNOWN", "Missing decision latency cannot be imputed to zero.", [replace("/timeline/decided_at", None)],
         [eq("/options/0/time_target_using_upper_bound", "unknown"), eq("/metrics_minutes/detection_to_decision", None)])
    case("INVALID-NAIVE-TIME", "Timezone-free timestamps are deliberate input rejection, not guessed UTC.", [replace("/timeline/detected_at", "2026-09-01T09:03:00")])
    case("INVALID-BOOL-MINUTES", "Boolean true is not one minute.", [replace("/targets/recovery_minutes", True)])
    case("INVALID-ENUM-CONTAINER", "Malformed strategy containers produce deliberate rejection, not a TypeError crash.", [replace("/options/0/strategy", [])])
    case("INVALID-NEGATIVE-MINUTES", "Negative objective is not interpreted as an instant target.", [replace("/targets/recovery_minutes", -1)])
    case("INVALID-DUPLICATE-ID", "Duplicate evidence identity is not last-write-wins.", [{"op": "append", "path": "/evidence", "value": copy.deepcopy(config["evidence"][0])}])
    case("INVALID-DANGLING-REFERENCE", "Unknown verification references produce explicit input rejection.", [replace("/recovery/checks/0/evidence_ids/0", "does-not-exist")])
    return validate_suite(suite)


if __name__ == "__main__":
    print(json.dumps(make_suite(), indent=2, ensure_ascii=False, allow_nan=False))
