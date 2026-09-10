"""Exact schema validators for release policy, bank, report, and receipt."""

from __future__ import annotations

from typing import Any

from admission_common import (
    AdmissionError,
    SCHEMA_VERSION,
    digest_canonical,
    require_array,
    require_bool,
    require_decimal,
    require_exact_keys,
    require_hex,
    require_int,
    require_object,
    require_string,
    validate_manifest,
)


def validate_policy(policy: Any) -> dict[str, Any]:
    obj = require_object(policy, "policy")
    keys = {
        "schema_version",
        "minimum_seed_count",
        "minimum_action_active_cells",
        "minimum_world_active_cells",
        "minimum_global_mean_own_delta",
        "minimum_global_mean_margin_delta",
        "minimum_stratum_mean_own_delta",
        "minimum_stratum_mean_margin_delta",
        "minimum_seed_mean_own_delta",
        "minimum_seed_mean_margin_delta",
        "minimum_cell_own_delta",
        "minimum_cell_margin_delta",
        "require_zero_lost_wins",
        "require_zero_new_losses",
    }
    require_exact_keys(obj, keys, "policy")
    if require_int(obj["schema_version"], "policy.schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported policy.schema_version")
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "minimum_seed_count": require_int(
            obj["minimum_seed_count"], "policy.minimum_seed_count", minimum=1
        ),
        "minimum_action_active_cells": require_int(
            obj["minimum_action_active_cells"],
            "policy.minimum_action_active_cells",
            minimum=1,
        ),
        "minimum_world_active_cells": require_int(
            obj["minimum_world_active_cells"],
            "policy.minimum_world_active_cells",
            minimum=1,
        ),
        "require_zero_lost_wins": require_bool(
            obj["require_zero_lost_wins"], "policy.require_zero_lost_wins"
        ),
        "require_zero_new_losses": require_bool(
            obj["require_zero_new_losses"], "policy.require_zero_new_losses"
        ),
    }
    for key in sorted(
        keys
        - {
            "schema_version",
            "minimum_seed_count",
            "minimum_action_active_cells",
            "minimum_world_active_cells",
            "require_zero_lost_wins",
            "require_zero_new_losses",
        }
    ):
        result[key] = require_decimal(obj[key], f"policy.{key}")
    return result


def validate_bank(bank: Any) -> dict[str, Any]:
    obj = require_object(bank, "receipt.bank")
    require_exact_keys(obj, {"bank_id", "bank_sha256", "opponents", "seeds", "seats"}, "receipt.bank")
    bank_id = require_string(obj["bank_id"], "receipt.bank.bank_id")
    bank_sha = require_hex(obj["bank_sha256"], "receipt.bank.bank_sha256", 64)

    opponent_rows = require_array(obj["opponents"], "receipt.bank.opponents")
    if not opponent_rows:
        raise AdmissionError("receipt.bank.opponents must not be empty")
    opponents: list[dict[str, Any]] = []
    names: list[str] = []
    for index, row in enumerate(opponent_rows):
        label = f"receipt.bank.opponents[{index}]"
        item = require_object(row, label)
        require_exact_keys(item, {"name", "archive_sha256", "tree_sha256"}, label)
        name = require_string(item["name"], f"{label}.name")
        opponents.append(
            {
                "name": name,
                "archive_sha256": require_hex(
                    item["archive_sha256"], f"{label}.archive_sha256", 64
                ),
                "tree_sha256": require_hex(item["tree_sha256"], f"{label}.tree_sha256", 64),
            }
        )
        names.append(name)
    if names != sorted(names):
        raise AdmissionError("receipt.bank.opponents must be sorted by name")
    if len(names) != len(set(names)):
        raise AdmissionError("receipt.bank.opponents contains duplicate names")

    raw_seeds = require_array(obj["seeds"], "receipt.bank.seeds")
    seeds = [require_int(value, f"receipt.bank.seeds[{index}]", minimum=0) for index, value in enumerate(raw_seeds)]
    if not seeds:
        raise AdmissionError("receipt.bank.seeds must not be empty")
    if seeds != sorted(seeds) or len(seeds) != len(set(seeds)):
        raise AdmissionError("receipt.bank.seeds must be unique and sorted")

    raw_seats = require_array(obj["seats"], "receipt.bank.seats")
    seats = [require_int(value, f"receipt.bank.seats[{index}]") for index, value in enumerate(raw_seats)]
    if seats != [0, 1]:
        raise AdmissionError("receipt.bank.seats must be exactly [0, 1]")

    body = {"bank_id": bank_id, "opponents": opponents, "seeds": seeds, "seats": seats}
    computed = digest_canonical(body)
    if computed != bank_sha:
        raise AdmissionError(
            f"receipt.bank.bank_sha256 mismatch: declared={bank_sha} computed={computed}"
        )
    return {**body, "bank_sha256": bank_sha}


def validate_score_record(raw: Any, label: str) -> dict[str, Any]:
    obj = require_object(raw, label)
    require_exact_keys(
        obj,
        {"own", "rival", "trace_steps", "action_trace_sha256", "world_trace_sha256"},
        label,
    )
    return {
        "own": require_decimal(obj["own"], f"{label}.own"),
        "rival": require_decimal(obj["rival"], f"{label}.rival"),
        "trace_steps": require_int(obj["trace_steps"], f"{label}.trace_steps", minimum=1),
        "action_trace_sha256": require_hex(
            obj["action_trace_sha256"], f"{label}.action_trace_sha256", 64
        ),
        "world_trace_sha256": require_hex(
            obj["world_trace_sha256"], f"{label}.world_trace_sha256", 64
        ),
    }


def validate_first_divergence(raw: Any, label: str) -> dict[str, Any] | None:
    if raw is None:
        return None
    obj = require_object(raw, label)
    keys = {
        "step",
        "baseline_preworld_sha256",
        "candidate_preworld_sha256",
        "baseline_focal_action_sha256",
        "candidate_focal_action_sha256",
        "baseline_rival_action_sha256",
        "candidate_rival_action_sha256",
        "baseline_postworld_sha256",
        "candidate_postworld_sha256",
    }
    require_exact_keys(obj, keys, label)
    result: dict[str, Any] = {"step": require_int(obj["step"], f"{label}.step", minimum=0)}
    for key in sorted(keys - {"step"}):
        result[key] = require_hex(obj[key], f"{label}.{key}", 64)
    return result


def validate_report(report: Any) -> dict[str, Any]:
    obj = require_object(report, "report")
    keys = {
        "schema_version",
        "bank_id",
        "candidate_head_commit",
        "baseline_tree_sha256",
        "candidate_tree_sha256",
        "engine_sha256",
        "evaluator_sha256",
        "cells",
    }
    require_exact_keys(obj, keys, "report")
    if require_int(obj["schema_version"], "report.schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported report.schema_version")
    cells_raw = require_array(obj["cells"], "report.cells")
    cells: list[dict[str, Any]] = []
    for index, raw_cell in enumerate(cells_raw):
        label = f"report.cells[{index}]"
        cell = require_object(raw_cell, label)
        require_exact_keys(
            cell,
            {"opponent", "seed", "seat", "baseline", "candidate", "first_divergence"},
            label,
        )
        cells.append(
            {
                "opponent": require_string(cell["opponent"], f"{label}.opponent"),
                "seed": require_int(cell["seed"], f"{label}.seed", minimum=0),
                "seat": require_int(cell["seat"], f"{label}.seat"),
                "baseline": validate_score_record(cell["baseline"], f"{label}.baseline"),
                "candidate": validate_score_record(cell["candidate"], f"{label}.candidate"),
                "first_divergence": validate_first_divergence(
                    cell["first_divergence"], f"{label}.first_divergence"
                ),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "bank_id": require_string(obj["bank_id"], "report.bank_id"),
        "candidate_head_commit": require_hex(
            obj["candidate_head_commit"], "report.candidate_head_commit", 40
        ),
        "baseline_tree_sha256": require_hex(
            obj["baseline_tree_sha256"], "report.baseline_tree_sha256", 64
        ),
        "candidate_tree_sha256": require_hex(
            obj["candidate_tree_sha256"], "report.candidate_tree_sha256", 64
        ),
        "engine_sha256": require_hex(obj["engine_sha256"], "report.engine_sha256", 64),
        "evaluator_sha256": require_hex(
            obj["evaluator_sha256"], "report.evaluator_sha256", 64
        ),
        "cells": cells,
    }


def validate_receipt(receipt: Any) -> dict[str, Any]:
    obj = require_object(receipt, "receipt")
    keys = {"schema_version", "candidate", "packages", "workflow", "bank", "policy", "report"}
    require_exact_keys(obj, keys, "receipt")
    if require_int(obj["schema_version"], "receipt.schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported receipt.schema_version")

    candidate_raw = require_object(obj["candidate"], "receipt.candidate")
    candidate_keys = {
        "name",
        "base_commit",
        "head_commit",
        "pr_head_commit",
        "source_sha256",
        "engine_sha256",
        "evaluator_sha256",
    }
    require_exact_keys(candidate_raw, candidate_keys, "receipt.candidate")
    candidate = {
        "name": require_string(candidate_raw["name"], "receipt.candidate.name"),
        "base_commit": require_hex(candidate_raw["base_commit"], "receipt.candidate.base_commit", 40),
        "head_commit": require_hex(candidate_raw["head_commit"], "receipt.candidate.head_commit", 40),
        "pr_head_commit": require_hex(
            candidate_raw["pr_head_commit"], "receipt.candidate.pr_head_commit", 40
        ),
        "source_sha256": require_hex(
            candidate_raw["source_sha256"], "receipt.candidate.source_sha256", 64
        ),
        "engine_sha256": require_hex(
            candidate_raw["engine_sha256"], "receipt.candidate.engine_sha256", 64
        ),
        "evaluator_sha256": require_hex(
            candidate_raw["evaluator_sha256"], "receipt.candidate.evaluator_sha256", 64
        ),
    }

    packages_raw = require_object(obj["packages"], "receipt.packages")
    require_exact_keys(packages_raw, {"baseline", "candidate"}, "receipt.packages")
    packages = {
        "baseline": validate_manifest(packages_raw["baseline"], "receipt.packages.baseline"),
        "candidate": validate_manifest(packages_raw["candidate"], "receipt.packages.candidate"),
    }

    workflow_raw = require_object(obj["workflow"], "receipt.workflow")
    workflow_keys = {
        "run_id",
        "status",
        "conclusion",
        "attempt",
        "head_sha",
        "baseline_artifact_sha256",
        "baseline_artifact_bytes",
        "candidate_artifact_sha256",
        "candidate_artifact_bytes",
        "report_artifact_sha256",
        "report_artifact_bytes",
    }
    require_exact_keys(workflow_raw, workflow_keys, "receipt.workflow")
    workflow = {
        "run_id": require_int(workflow_raw["run_id"], "receipt.workflow.run_id", minimum=1),
        "status": require_string(workflow_raw["status"], "receipt.workflow.status"),
        "conclusion": require_string(workflow_raw["conclusion"], "receipt.workflow.conclusion"),
        "attempt": require_int(workflow_raw["attempt"], "receipt.workflow.attempt", minimum=1),
        "head_sha": require_hex(workflow_raw["head_sha"], "receipt.workflow.head_sha", 40),
        "baseline_artifact_sha256": require_hex(
            workflow_raw["baseline_artifact_sha256"],
            "receipt.workflow.baseline_artifact_sha256",
            64,
        ),
        "baseline_artifact_bytes": require_int(
            workflow_raw["baseline_artifact_bytes"],
            "receipt.workflow.baseline_artifact_bytes",
            minimum=1,
        ),
        "candidate_artifact_sha256": require_hex(
            workflow_raw["candidate_artifact_sha256"],
            "receipt.workflow.candidate_artifact_sha256",
            64,
        ),
        "candidate_artifact_bytes": require_int(
            workflow_raw["candidate_artifact_bytes"],
            "receipt.workflow.candidate_artifact_bytes",
            minimum=1,
        ),
        "report_artifact_sha256": require_hex(
            workflow_raw["report_artifact_sha256"],
            "receipt.workflow.report_artifact_sha256",
            64,
        ),
        "report_artifact_bytes": require_int(
            workflow_raw["report_artifact_bytes"],
            "receipt.workflow.report_artifact_bytes",
            minimum=1,
        ),
    }

    policy_raw = require_object(obj["policy"], "receipt.policy")
    require_exact_keys(policy_raw, {"sha256", "bytes"}, "receipt.policy")
    policy_ref = {
        "sha256": require_hex(policy_raw["sha256"], "receipt.policy.sha256", 64),
        "bytes": require_int(policy_raw["bytes"], "receipt.policy.bytes", minimum=1),
    }

    report_raw = require_object(obj["report"], "receipt.report")
    require_exact_keys(report_raw, {"sha256", "bytes"}, "receipt.report")
    report_ref = {
        "sha256": require_hex(report_raw["sha256"], "receipt.report.sha256", 64),
        "bytes": require_int(report_raw["bytes"], "receipt.report.bytes", minimum=1),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "candidate": candidate,
        "packages": packages,
        "workflow": workflow,
        "bank": validate_bank(obj["bank"]),
        "policy": policy_ref,
        "report": report_ref,
    }

