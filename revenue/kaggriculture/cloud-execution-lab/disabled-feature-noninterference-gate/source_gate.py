"""Source-contract validation and source audit receipt construction."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from gate_common import (
    GATE_NAME, SCHEMA_VERSION, GateError, _DOTTED, _require_exact_keys,
    _require_nonempty_string, _require_object, _require_verdict,
    _resolve_under, _safe_relative_path, canonical_bytes, git_blob_sha1,
    sha256_bytes,
)
from source_analysis import SourceAnalyzer

def validate_source_contract(raw: Any) -> dict[str, Any]:
    contract = _require_object(raw, "source contract")
    _require_exact_keys(
        contract,
        required={
            "schema_version",
            "claim_id",
            "source",
            "target",
            "disabled_bindings",
            "protected_effects",
            "expected_verdict",
        },
        optional=set(),
        label="source contract",
    )
    if contract["schema_version"] != SCHEMA_VERSION:
        raise GateError(f"source contract schema_version must be {SCHEMA_VERSION}")
    claim_id = _require_nonempty_string(contract["claim_id"], "claim_id")
    expected = _require_verdict(contract["expected_verdict"], "expected_verdict")

    source = _require_object(contract["source"], "source")
    _require_exact_keys(
        source,
        required={"path", "git_blob_sha1"},
        optional=set(),
        label="source",
    )
    source_path = _safe_relative_path(source["path"], "source.path")
    blob = _require_nonempty_string(source["git_blob_sha1"], "source.git_blob_sha1")
    if not re.fullmatch(r"[0-9a-f]{40}", blob):
        raise GateError("source.git_blob_sha1 must be a lowercase 40-hex Git blob id")

    target = _require_object(contract["target"], "target")
    _require_exact_keys(target, required={"class", "method"}, optional=set(), label="target")
    class_name = _require_nonempty_string(target["class"], "target.class")
    method_name = _require_nonempty_string(target["method"], "target.method")
    if not class_name.isidentifier() or not method_name.isidentifier():
        raise GateError("target.class and target.method must be Python identifiers")

    bindings = _require_object(contract["disabled_bindings"], "disabled_bindings")
    if not bindings:
        raise GateError("disabled_bindings must not be empty")
    normalized_bindings: dict[str, bool] = {}
    for name, value in bindings.items():
        if not isinstance(name, str) or not _DOTTED.fullmatch(name):
            raise GateError(f"disabled binding {name!r} must be a dotted identifier")
        if value is not False:
            raise GateError(f"disabled binding {name} must be the boolean false")
        normalized_bindings[name] = False

    effects = contract["protected_effects"]
    if not isinstance(effects, list) or not effects:
        raise GateError("protected_effects must be a non-empty list")
    normalized_effects: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(effects):
        effect = _require_object(item, f"protected_effects[{index}]")
        _require_exact_keys(
            effect,
            required={"kind", "target"},
            optional=set(),
            label=f"protected_effects[{index}]",
        )
        kind = _require_nonempty_string(effect["kind"], f"protected_effects[{index}].kind")
        if kind not in {"call", "write"}:
            raise GateError(f"protected_effects[{index}].kind must be call or write")
        effect_target = _require_nonempty_string(
            effect["target"], f"protected_effects[{index}].target"
        )
        if not _DOTTED.fullmatch(effect_target):
            raise GateError(f"protected effect target {effect_target!r} must be dotted")
        key = (kind, effect_target)
        if key in seen:
            raise GateError(f"duplicate protected effect: {kind} {effect_target}")
        seen.add(key)
        normalized_effects.append({"kind": kind, "target": effect_target})

    return {
        "schema_version": SCHEMA_VERSION,
        "claim_id": claim_id,
        "source": {"path": source_path, "git_blob_sha1": blob},
        "target": {"class": class_name, "method": method_name},
        "disabled_bindings": dict(sorted(normalized_bindings.items())),
        "protected_effects": sorted(normalized_effects, key=lambda item: (item["kind"], item["target"])),
        "expected_verdict": expected,
    }


def audit_source(repo_root: Path, raw_contract: Any) -> dict[str, Any]:
    contract = validate_source_contract(raw_contract)
    source_path = _resolve_under(repo_root, contract["source"]["path"], "source.path")
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        raise GateError(f"cannot read source {contract['source']['path']}: {exc}") from exc
    observed_blob = git_blob_sha1(source_bytes)
    expected_blob = contract["source"]["git_blob_sha1"]
    if observed_blob != expected_blob:
        raise GateError(
            f"source drift: expected Git blob {expected_blob}, observed {observed_blob}"
        )
    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("source must be UTF-8") from exc
    try:
        tree = ast.parse(source_text, filename=contract["source"]["path"])
    except SyntaxError as exc:
        raise GateError(f"source is not valid Python: {exc}") from exc

    class_name = contract["target"]["class"]
    method_name = contract["target"]["method"]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    if len(classes) != 1:
        raise GateError(f"expected exactly one top-level class {class_name}, found {len(classes)}")
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name
    ]
    if len(methods) != 1:
        raise GateError(
            f"expected exactly one direct method {class_name}.{method_name}, found {len(methods)}"
        )

    protected_calls = {
        item["target"] for item in contract["protected_effects"] if item["kind"] == "call"
    }
    protected_writes = {
        item["target"] for item in contract["protected_effects"] if item["kind"] == "write"
    }
    analyzer = SourceAnalyzer(
        bindings=contract["disabled_bindings"],
        protected_calls=protected_calls,
        protected_writes=protected_writes,
    )
    analyzer.execute_block(methods[0].body)
    findings = [item.as_dict() for item in sorted(analyzer.findings)]
    observed = "PASS" if not findings else "BLOCK"
    expected = contract["expected_verdict"]
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE_NAME,
        "mode": "source",
        "claim_id": contract["claim_id"],
        "expected_verdict": expected,
        "observed_verdict": observed,
        "expectation_met": observed == expected,
        "source": {
            "path": contract["source"]["path"],
            "git_blob_sha1": observed_blob,
            "sha256": sha256_bytes(source_bytes),
        },
        "contract_sha256": sha256_bytes(canonical_bytes(contract)),
        "target": contract["target"],
        "disabled_bindings": contract["disabled_bindings"],
        "protected_effects": contract["protected_effects"],
        "findings": findings,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt


