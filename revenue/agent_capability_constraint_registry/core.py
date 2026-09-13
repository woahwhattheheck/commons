"""Deterministic, execution-free agent capability and constraint registry.

The registry compiles a strict JSON census into content-addressed JSON/Markdown
projections plus an independently verifiable receipt.  It never executes tools,
selects models, deploys agents, or authorizes any external effect.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA = "agent-capability-constraint-registry/input/v1"
RESULT_SCHEMA = "agent-capability-constraint-registry/result/v1"
RECEIPT_SCHEMA = "agent-capability-constraint-registry/receipt/v1"
VALID_STATUSES = ("READY", "TOOLING_NEEDED", "OWNER_DECISION", "HOLD")
OWNER_VERDICTS = {"APPROVED", "PENDING", "DENIED", "NOT_REQUIRED"}
CAPABILITY_CONDITIONS = {"PASS", "PARTIAL", "FAIL"}
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RFC3339_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class RegistryError(ValueError):
    """Fail-closed validation or verification error."""


class _DuplicateKeyError(RegistryError):
    pass


@dataclass(frozen=True)
class CompiledRegistry:
    result: dict[str, Any]
    result_bytes: bytes
    markdown_bytes: bytes
    receipt: dict[str, Any]
    receipt_bytes: bytes


def _reject_constant(value: str) -> None:
    raise RegistryError(f"non-finite JSON number forbidden: {value}")


def _reject_float(value: str) -> None:
    raise RegistryError(f"floating-point JSON number forbidden: {value}")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json_bytes(raw: bytes, label: str = "input") -> dict[str, Any]:
    """Load UTF-8 JSON with duplicate-key, float and non-finite rejection."""
    if not isinstance(raw, (bytes, bytearray)):
        raise RegistryError(f"{label}: bytes required")
    if bytes(raw).startswith(b"\xef\xbb\xbf"):
        raise RegistryError(f"{label}: UTF-8 BOM forbidden")
    try:
        text = bytes(raw).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RegistryError(f"{label}: invalid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except RegistryError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RegistryError(f"{label}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise RegistryError(f"{label}: top level must be an object")
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_exact_keys(obj: dict[str, Any], keys: set[str], where: str) -> None:
    got = set(obj)
    if got != keys:
        missing = sorted(keys - got)
        extra = sorted(got - keys)
        raise RegistryError(f"{where}: keys mismatch missing={missing} extra={extra}")


def _require_str(value: Any, where: str, *, token: bool = False, max_len: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len:
        raise RegistryError(f"{where}: non-empty string <= {max_len} chars required")
    if any(ord(ch) < 32 for ch in value):
        raise RegistryError(f"{where}: control characters forbidden")
    if token and not _TOKEN_RE.fullmatch(value):
        raise RegistryError(f"{where}: invalid token")
    return value


def _require_int(value: Any, where: str, *, minimum: int = 0, maximum: int = 10**9) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RegistryError(f"{where}: integer required (bool forbidden)")
    if not (minimum <= value <= maximum):
        raise RegistryError(f"{where}: integer out of range")
    return value


def _require_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise RegistryError(f"{where}: boolean required")
    return value


def _require_sha256(value: Any, where: str) -> str:
    text = _require_str(value, where, max_len=64)
    if not _SHA256_RE.fullmatch(text):
        raise RegistryError(f"{where}: lowercase sha256 required")
    return text


def _require_timestamp(value: Any, where: str) -> str:
    text = _require_str(value, where, max_len=20)
    if not _RFC3339_Z_RE.fullmatch(text):
        raise RegistryError(f"{where}: RFC3339 UTC second timestamp required")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise RegistryError(f"{where}: invalid UTC timestamp") from exc
    return text


def _require_str_list(value: Any, where: str, *, token: bool = True, max_items: int = 64) -> list[str]:
    if not isinstance(value, list) or len(value) > max_items:
        raise RegistryError(f"{where}: list with <= {max_items} items required")
    out: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(value):
        text = _require_str(item, f"{where}[{idx}]", token=token)
        if text in seen:
            raise RegistryError(f"{where}: duplicate item {text}")
        seen.add(text)
        out.append(text)
    return sorted(out)


def _normalize_capability(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegistryError(f"{where}: object required")
    _require_exact_keys(value, {"capability", "evidence_ref", "evidence_sha256", "measured_at", "condition"}, where)
    condition = _require_str(value["condition"], f"{where}.condition", token=True)
    if condition not in CAPABILITY_CONDITIONS:
        raise RegistryError(f"{where}.condition: invalid value")
    return {
        "capability": _require_str(value["capability"], f"{where}.capability", token=True),
        "condition": condition,
        "evidence_ref": _require_str(value["evidence_ref"], f"{where}.evidence_ref", max_len=512),
        "evidence_sha256": _require_sha256(value["evidence_sha256"], f"{where}.evidence_sha256"),
        "measured_at": _require_timestamp(value["measured_at"], f"{where}.measured_at"),
    }


def _normalize_constraint(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegistryError(f"{where}: object required")
    _require_exact_keys(
        value,
        {"constraint", "source_ref", "source_sha256", "tooling_need", "owner_verdict", "estimated_fix_minutes"},
        where,
    )
    verdict = _require_str(value["owner_verdict"], f"{where}.owner_verdict", token=True)
    if verdict not in OWNER_VERDICTS:
        raise RegistryError(f"{where}.owner_verdict: invalid value")
    tooling_need = _require_str(value["tooling_need"], f"{where}.tooling_need", token=True)
    return {
        "constraint": _require_str(value["constraint"], f"{where}.constraint", token=True),
        "estimated_fix_minutes": _require_int(value["estimated_fix_minutes"], f"{where}.estimated_fix_minutes", minimum=0, maximum=525600),
        "owner_verdict": verdict,
        "source_ref": _require_str(value["source_ref"], f"{where}.source_ref", max_len=512),
        "source_sha256": _require_sha256(value["source_sha256"], f"{where}.source_sha256"),
        "tooling_need": tooling_need,
    }


def _normalize_record(value: Any, index: int) -> dict[str, Any]:
    where = f"records[{index}]"
    if not isinstance(value, dict):
        raise RegistryError(f"{where}: object required")
    _require_exact_keys(
        value,
        {
            "agent_id", "workstream", "provider", "model_or_harness", "revision",
            "measured_capabilities", "declared_constraints", "required_tools",
            "available_tools", "owner_decision", "blocking_reasons", "execution_requested",
        },
        where,
    )
    revision = _require_int(value["revision"], f"{where}.revision", minimum=1, maximum=10**6)
    owner_decision = _require_str(value["owner_decision"], f"{where}.owner_decision", token=True)
    if owner_decision not in OWNER_VERDICTS:
        raise RegistryError(f"{where}.owner_decision: invalid value")
    execution_requested = _require_bool(value["execution_requested"], f"{where}.execution_requested")

    caps_raw = value["measured_capabilities"]
    if not isinstance(caps_raw, list) or not (1 <= len(caps_raw) <= 128):
        raise RegistryError(f"{where}.measured_capabilities: 1..128 items required")
    caps = [_normalize_capability(item, f"{where}.measured_capabilities[{idx}]") for idx, item in enumerate(caps_raw)]
    cap_names = [item["capability"] for item in caps]
    if len(cap_names) != len(set(cap_names)):
        raise RegistryError(f"{where}.measured_capabilities: duplicate capability")
    caps.sort(key=lambda item: item["capability"])

    constraints_raw = value["declared_constraints"]
    if not isinstance(constraints_raw, list) or len(constraints_raw) > 128:
        raise RegistryError(f"{where}.declared_constraints: <=128 items required")
    constraints = [_normalize_constraint(item, f"{where}.declared_constraints[{idx}]") for idx, item in enumerate(constraints_raw)]
    constraint_names = [item["constraint"] for item in constraints]
    if len(constraint_names) != len(set(constraint_names)):
        raise RegistryError(f"{where}.declared_constraints: duplicate constraint")
    constraints.sort(key=lambda item: item["constraint"])

    return {
        "agent_id": _require_str(value["agent_id"], f"{where}.agent_id", token=True),
        "available_tools": _require_str_list(value["available_tools"], f"{where}.available_tools"),
        "blocking_reasons": _require_str_list(value["blocking_reasons"], f"{where}.blocking_reasons"),
        "declared_constraints": constraints,
        "execution_requested": execution_requested,
        "measured_capabilities": caps,
        "model_or_harness": _require_str(value["model_or_harness"], f"{where}.model_or_harness", token=True),
        "owner_decision": owner_decision,
        "provider": _require_str(value["provider"], f"{where}.provider", token=True),
        "required_tools": _require_str_list(value["required_tools"], f"{where}.required_tools"),
        "revision": revision,
        "workstream": _require_str(value["workstream"], f"{where}.workstream", token=True),
    }


def normalize_input(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegistryError("input: object required")
    _require_exact_keys(value, {"schema", "registry_id", "snapshot_ref", "snapshot_sha256", "generated_at", "records"}, "input")
    if value["schema"] != INPUT_SCHEMA:
        raise RegistryError("input.schema: unsupported schema")
    records_raw = value["records"]
    if not isinstance(records_raw, list) or not (1 <= len(records_raw) <= 4096):
        raise RegistryError("input.records: 1..4096 items required")
    records = [_normalize_record(item, idx) for idx, item in enumerate(records_raw)]
    identities: set[tuple[str, int]] = set()
    for record in records:
        identity = (record["agent_id"], record["revision"])
        if identity in identities:
            raise RegistryError(f"input.records: duplicate agent/revision identity {identity[0]}@{identity[1]}")
        identities.add(identity)
    records.sort(key=lambda item: (item["workstream"], item["agent_id"], item["revision"]))
    return {
        "generated_at": _require_timestamp(value["generated_at"], "input.generated_at"),
        "records": records,
        "registry_id": _require_str(value["registry_id"], "input.registry_id", token=True),
        "schema": INPUT_SCHEMA,
        "snapshot_ref": _require_str(value["snapshot_ref"], "input.snapshot_ref", max_len=512),
        "snapshot_sha256": _require_sha256(value["snapshot_sha256"], "input.snapshot_sha256"),
    }


def _classify(record: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    missing_tools = sorted(set(record["required_tools"]) - set(record["available_tools"]))
    reasons: list[str] = []

    failed_caps = [item["capability"] for item in record["measured_capabilities"] if item["condition"] == "FAIL"]
    denied_constraints = [item["constraint"] for item in record["declared_constraints"] if item["owner_verdict"] == "DENIED"]
    pending_constraints = [item["constraint"] for item in record["declared_constraints"] if item["owner_verdict"] == "PENDING"]
    tooling_constraints = [
        item["tooling_need"] for item in record["declared_constraints"] if item["tooling_need"] != "NONE"
    ]

    if record["execution_requested"]:
        reasons.append("EXECUTION_REQUESTED_OUTSIDE_REGISTRY_AUTHORITY")
    reasons.extend(f"BLOCK:{item}" for item in record["blocking_reasons"])
    reasons.extend(f"CAPABILITY_FAIL:{item}" for item in failed_caps)
    reasons.extend(f"CONSTRAINT_DENIED:{item}" for item in denied_constraints)

    if reasons:
        return "HOLD", sorted(reasons), missing_tools
    if record["owner_decision"] == "DENIED":
        return "HOLD", ["OWNER_DENIED"], missing_tools
    if record["owner_decision"] == "PENDING" or pending_constraints:
        details = ["OWNER_DECISION_PENDING"]
        details.extend(f"CONSTRAINT_PENDING:{item}" for item in pending_constraints)
        return "OWNER_DECISION", sorted(details), missing_tools
    if missing_tools or tooling_constraints:
        details = [f"MISSING_TOOL:{item}" for item in missing_tools]
        details.extend(f"TOOLING_CONSTRAINT:{item}" for item in tooling_constraints)
        return "TOOLING_NEEDED", sorted(details), missing_tools
    return "READY", [], []


def _projection_record(record: dict[str, Any]) -> dict[str, Any]:
    status, reasons, missing_tools = _classify(record)
    return {
        **deepcopy(record),
        "missing_tools": missing_tools,
        "status": status,
        "status_reasons": reasons,
    }


def _markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_markdown(result: dict[str, Any]) -> bytes:
    lines = [
        "# Agent Capability & Constraint Registry",
        "",
        f"- Registry: `{_markdown_escape(result['registry_id'])}`",
        f"- Generated at: `{result['generated_at']}`",
        f"- Snapshot: `{_markdown_escape(result['snapshot_ref'])}` / `{result['snapshot_sha256']}`",
        f"- Input SHA-256: `{result['input_sha256']}`",
        "- Authority: **observational only; no execution, deployment, access, spend, messaging, or model-selection authority**",
        "",
        "| Workstream | Agent | Rev | Provider | Model/Harness | Status | Reasons |",
        "|---|---|---:|---|---|---|---|",
    ]
    for record in result["records"]:
        reasons = ", ".join(record["status_reasons"]) if record["status_reasons"] else "—"
        lines.append(
            "| " + " | ".join([
                _markdown_escape(record["workstream"]),
                _markdown_escape(record["agent_id"]),
                str(record["revision"]),
                _markdown_escape(record["provider"]),
                _markdown_escape(record["model_or_harness"]),
                record["status"],
                _markdown_escape(reasons),
            ]) + " |"
        )
    lines.extend(["", "## Counts", ""])
    for status in VALID_STATUSES:
        lines.append(f"- `{status}`: {result['counts'][status]}")
    lines.extend([
        "",
        "## Non-authority boundary",
        "",
        "This projection is an evidence-backed census. A `READY` row means only that the declared registry conditions are internally satisfied. It is **not** permission to run, deploy, call a tool, access data, message anyone, spend money, or change external state.",
        "",
    ])
    return "\n".join(lines).encode("utf-8")


def compile_registry(value: dict[str, Any]) -> CompiledRegistry:
    normalized = normalize_input(value)
    normalized_bytes = _canonical_json_bytes(normalized)
    input_digest = _sha256(normalized_bytes)
    projected = [_projection_record(record) for record in normalized["records"]]
    counts = {status: 0 for status in VALID_STATUSES}
    for record in projected:
        counts[record["status"]] += 1
    result = {
        "authority": {
            "access_elevation": False,
            "deployment": False,
            "external_effects": False,
            "messaging": False,
            "model_selection": False,
            "spending": False,
            "tool_execution": False,
        },
        "counts": counts,
        "generated_at": normalized["generated_at"],
        "input_sha256": input_digest,
        "records": projected,
        "registry_id": normalized["registry_id"],
        "schema": RESULT_SCHEMA,
        "snapshot_ref": normalized["snapshot_ref"],
        "snapshot_sha256": normalized["snapshot_sha256"],
    }
    result_raw = _canonical_json_bytes(result)
    markdown_raw = render_markdown(result)
    receipt_base = {
        "authority": "OBSERVATIONAL_ONLY",
        "input_sha256": input_digest,
        "markdown_sha256": _sha256(markdown_raw),
        "record_count": len(projected),
        "registry_id": normalized["registry_id"],
        "result_sha256": _sha256(result_raw),
        "schema": RECEIPT_SCHEMA,
    }
    receipt = {**receipt_base, "receipt_sha256": _sha256(_canonical_json_bytes(receipt_base))}
    receipt_raw = _canonical_json_bytes(receipt)
    return CompiledRegistry(result, result_raw, markdown_raw, receipt, receipt_raw)


def verify_compiled(
    source: dict[str, Any],
    result_raw: bytes,
    markdown_raw: bytes,
    receipt_raw: bytes,
) -> dict[str, Any]:
    """Recompile source and byte-verify all outputs and receipt commitments."""
    expected = compile_registry(source)
    observed_result = load_json_bytes(result_raw, "result")
    observed_receipt = load_json_bytes(receipt_raw, "receipt")
    if observed_result.get("schema") != RESULT_SCHEMA:
        raise RegistryError("result: unsupported schema")
    if observed_receipt.get("schema") != RECEIPT_SCHEMA:
        raise RegistryError("receipt: unsupported schema")
    if result_raw != expected.result_bytes:
        raise RegistryError("result: bytes or semantics do not match deterministic recompile")
    if markdown_raw != expected.markdown_bytes:
        raise RegistryError("markdown: bytes do not match deterministic recompile")
    if receipt_raw != expected.receipt_bytes:
        raise RegistryError("receipt: bytes or commitments do not match deterministic recompile")
    receipt_base = dict(observed_receipt)
    claimed_receipt = receipt_base.pop("receipt_sha256", None)
    if claimed_receipt != _sha256(_canonical_json_bytes(receipt_base)):
        raise RegistryError("receipt: self commitment mismatch")
    return {
        "counts": expected.result["counts"],
        "input_sha256": expected.result["input_sha256"],
        "markdown_sha256": expected.receipt["markdown_sha256"],
        "receipt_sha256": expected.receipt["receipt_sha256"],
        "result_sha256": expected.receipt["result_sha256"],
        "verified": True,
    }


def write_compiled(source: dict[str, Any], out_dir: str | Path) -> CompiledRegistry:
    """Create a fresh output directory. Existing destinations fail closed."""
    dest = Path(out_dir)
    if dest.exists():
        raise RegistryError(f"output directory already exists: {dest}")
    compiled = compile_registry(source)
    dest.mkdir(parents=True, exist_ok=False)
    try:
        (dest / "registry.json").write_bytes(compiled.result_bytes)
        (dest / "registry.md").write_bytes(compiled.markdown_bytes)
        (dest / "receipt.json").write_bytes(compiled.receipt_bytes)
    except Exception:
        for child in dest.iterdir():
            child.unlink(missing_ok=True)
        dest.rmdir()
        raise
    return compiled
