from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1"
PASS = "PASS"
HOLD = "HOLD"
HEX64 = set("0123456789abcdef")
DEFECT_CODES = (
    "SPEC_REVISION_MISMATCH",
    "REGION_USE_CLAIM_MISMATCH",
    "LEGACY_MAPPING_MISMATCH",
    "STABILITY_MISMATCH",
    "OWNER_VERSION_MISMATCH",
)
FORBIDDEN_KEYS = {
    "email", "phone", "address", "street", "postal_code", "zip", "ssn", "dob", "date_of_birth"
}


class GateError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_no_duplicate_pairs)
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON: {exc.msg}") from exc


def _reject_pii_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise GateError(f"PII-shaped key forbidden at {path}.{key}")
            _reject_pii_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _reject_pii_keys(child, f"{path}[{i}]")


def _obj(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError(f"{field} must be an object")
    return value


def _arr(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateError(f"{field} must be an array")
    return value


def _text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise GateError(f"{field} must be a string" + ("" if allow_empty else " and non-empty"))
    return value.strip()


def _int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GateError(f"{field} must be integer >= {minimum}")
    return value


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in HEX64 for c in value)


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GateError("timestamp must be RFC3339 UTC ending in Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GateError(f"invalid UTC timestamp: {value}") from exc
    if dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise GateError("timestamp must resolve to UTC")
    return dt


def _unique_index(rows: list[dict[str, Any]], key: str, field: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(rows):
        rid = _text(row.get(key), f"{field}[{i}].{key}")
        if rid in out:
            raise GateError(f"duplicate {field} identifier: {rid}")
        out[rid] = row
    return out


def normalize_policy(value: Any) -> dict[str, Any]:
    p = _obj(value, "policy")
    allowed = {
        "policy_id", "policy_version", "max_snapshot_age_seconds", "approved_ingredients",
        "allowed_region_use_claims", "legacy_mappings", "stability_protocol_version",
        "owner_registry_version", "owners",
    }
    extra = set(p) - allowed
    if extra:
        raise GateError(f"unknown policy fields: {sorted(extra)}")
    ingredients = []
    for i, raw in enumerate(_arr(p.get("approved_ingredients"), "policy.approved_ingredients")):
        r = _obj(raw, f"policy.approved_ingredients[{i}]")
        if set(r) != {"ingredient_id", "spec_revision"}:
            raise GateError("approved ingredient fields must be ingredient_id,spec_revision")
        ingredients.append({
            "ingredient_id": _text(r.get("ingredient_id"), f"approved_ingredients[{i}].ingredient_id"),
            "spec_revision": _text(r.get("spec_revision"), f"approved_ingredients[{i}].spec_revision"),
        })
    ingredients.sort(key=lambda x: x["ingredient_id"])
    _unique_index(ingredients, "ingredient_id", "approved_ingredients")

    rules = []
    for i, raw in enumerate(_arr(p.get("allowed_region_use_claims"), "policy.allowed_region_use_claims")):
        r = _obj(raw, f"policy.allowed_region_use_claims[{i}]")
        required = {"ingredient_id", "region", "use_ref", "max_use_level_mgkg", "claim_ref"}
        if set(r) != required:
            raise GateError(f"region/use/claim fields must be {sorted(required)}")
        rules.append({
            "ingredient_id": _text(r.get("ingredient_id"), f"region_rule[{i}].ingredient_id"),
            "region": _text(r.get("region"), f"region_rule[{i}].region"),
            "use_ref": _text(r.get("use_ref"), f"region_rule[{i}].use_ref"),
            "max_use_level_mgkg": _int(r.get("max_use_level_mgkg"), f"region_rule[{i}].max_use_level_mgkg"),
            "claim_ref": _text(r.get("claim_ref"), f"region_rule[{i}].claim_ref"),
        })
    rules.sort(key=lambda x: (x["ingredient_id"], x["region"], x["use_ref"], x["claim_ref"], x["max_use_level_mgkg"]))
    if len({(r["ingredient_id"], r["region"], r["use_ref"], r["claim_ref"]) for r in rules}) != len(rules):
        raise GateError("duplicate region/use/claim rule")

    mappings = []
    for i, raw in enumerate(_arr(p.get("legacy_mappings"), "policy.legacy_mappings")):
        r = _obj(raw, f"policy.legacy_mappings[{i}]")
        if set(r) != {"legacy_id", "ingredient_id", "mapping_version"}:
            raise GateError("legacy mapping fields must be legacy_id,ingredient_id,mapping_version")
        mappings.append({
            "legacy_id": _text(r.get("legacy_id"), f"legacy_mappings[{i}].legacy_id"),
            "ingredient_id": _text(r.get("ingredient_id"), f"legacy_mappings[{i}].ingredient_id"),
            "mapping_version": _text(r.get("mapping_version"), f"legacy_mappings[{i}].mapping_version"),
        })
    mappings.sort(key=lambda x: x["legacy_id"])
    _unique_index(mappings, "legacy_id", "legacy_mappings")

    owners = []
    for i, raw in enumerate(_arr(p.get("owners"), "policy.owners")):
        r = _obj(raw, f"policy.owners[{i}]")
        if set(r) != {"owner_ref", "role", "owner_version"}:
            raise GateError("owner fields must be owner_ref,role,owner_version")
        role = _text(r.get("role"), f"owners[{i}].role")
        if role not in {"commercial", "science"}:
            raise GateError("owner role must be commercial or science")
        owners.append({
            "owner_ref": _text(r.get("owner_ref"), f"owners[{i}].owner_ref"),
            "role": role,
            "owner_version": _text(r.get("owner_version"), f"owners[{i}].owner_version"),
        })
    owners.sort(key=lambda x: x["owner_ref"])
    _unique_index(owners, "owner_ref", "owners")

    return {
        "policy_id": _text(p.get("policy_id"), "policy.policy_id"),
        "policy_version": _text(p.get("policy_version"), "policy.policy_version"),
        "max_snapshot_age_seconds": _int(p.get("max_snapshot_age_seconds"), "policy.max_snapshot_age_seconds"),
        "approved_ingredients": ingredients,
        "allowed_region_use_claims": rules,
        "legacy_mappings": mappings,
        "stability_protocol_version": _text(p.get("stability_protocol_version"), "policy.stability_protocol_version"),
        "owner_registry_version": _text(p.get("owner_registry_version"), "policy.owner_registry_version"),
        "owners": owners,
    }


def normalize_pack(value: Any, index: int) -> dict[str, Any]:
    r = _obj(value, f"solution_packs[{index}]")
    required = {
        "record_id", "ingredient_id", "spec_revision", "region", "use_ref", "use_level_mgkg",
        "claim_ref", "allergen_evidence_sha256", "label_evidence_sha256", "pilot_stability",
        "legacy_substitute", "commercial_owner_ref", "science_owner_ref", "owner_version", "source_sha256",
    }
    if set(r) != required:
        raise GateError(f"solution pack fields must be {sorted(required)}")
    stability = _obj(r.get("pilot_stability"), f"solution_packs[{index}].pilot_stability")
    if set(stability) != {"result_id", "status", "protocol_version", "evidence_sha256"}:
        raise GateError("pilot_stability fields invalid")
    legacy = _obj(r.get("legacy_substitute"), f"solution_packs[{index}].legacy_substitute")
    if set(legacy) != {"legacy_id", "mapping_version", "evidence_sha256"}:
        raise GateError("legacy_substitute fields invalid")
    return {
        "record_id": _text(r.get("record_id"), f"solution_packs[{index}].record_id"),
        "ingredient_id": _text(r.get("ingredient_id"), f"solution_packs[{index}].ingredient_id"),
        "spec_revision": _text(r.get("spec_revision"), f"solution_packs[{index}].spec_revision"),
        "region": _text(r.get("region"), f"solution_packs[{index}].region"),
        "use_ref": _text(r.get("use_ref"), f"solution_packs[{index}].use_ref"),
        "use_level_mgkg": _int(r.get("use_level_mgkg"), f"solution_packs[{index}].use_level_mgkg"),
        "claim_ref": _text(r.get("claim_ref"), f"solution_packs[{index}].claim_ref"),
        "allergen_evidence_sha256": _text(r.get("allergen_evidence_sha256"), f"solution_packs[{index}].allergen_evidence_sha256", allow_empty=True),
        "label_evidence_sha256": _text(r.get("label_evidence_sha256"), f"solution_packs[{index}].label_evidence_sha256", allow_empty=True),
        "pilot_stability": {
            "result_id": _text(stability.get("result_id"), "pilot_stability.result_id"),
            "status": _text(stability.get("status"), "pilot_stability.status"),
            "protocol_version": _text(stability.get("protocol_version"), "pilot_stability.protocol_version"),
            "evidence_sha256": _text(stability.get("evidence_sha256"), "pilot_stability.evidence_sha256", allow_empty=True),
        },
        "legacy_substitute": {
            "legacy_id": _text(legacy.get("legacy_id"), "legacy_substitute.legacy_id"),
            "mapping_version": _text(legacy.get("mapping_version"), "legacy_substitute.mapping_version"),
            "evidence_sha256": _text(legacy.get("evidence_sha256"), "legacy_substitute.evidence_sha256", allow_empty=True),
        },
        "commercial_owner_ref": _text(r.get("commercial_owner_ref"), "commercial_owner_ref", allow_empty=True),
        "science_owner_ref": _text(r.get("science_owner_ref"), "science_owner_ref", allow_empty=True),
        "owner_version": _text(r.get("owner_version"), "owner_version", allow_empty=True),
        "source_sha256": _text(r.get("source_sha256"), "source_sha256", allow_empty=True),
    }


def normalize_packet(value: Any) -> dict[str, Any]:
    _reject_pii_keys(value)
    p = _obj(value, "packet")
    if set(p) != {"schema_version", "snapshot", "policy", "solution_packs"}:
        raise GateError("packet fields must be schema_version,snapshot,policy,solution_packs")
    if p.get("schema_version") != SCHEMA_VERSION:
        raise GateError(f"schema_version must be {SCHEMA_VERSION}")
    snap = _obj(p.get("snapshot"), "snapshot")
    if set(snap) != {"snapshot_id", "captured_at", "source_system_ref"}:
        raise GateError("snapshot fields must be snapshot_id,captured_at,source_system_ref")
    packs = [normalize_pack(raw, i) for i, raw in enumerate(_arr(p.get("solution_packs"), "solution_packs"))]
    packs.sort(key=lambda x: x["record_id"])
    _unique_index(packs, "record_id", "solution_packs")
    out = {
        "schema_version": SCHEMA_VERSION,
        "snapshot": {
            "snapshot_id": _text(snap.get("snapshot_id"), "snapshot.snapshot_id"),
            "captured_at": _text(snap.get("captured_at"), "snapshot.captured_at"),
            "source_system_ref": _text(snap.get("source_system_ref"), "snapshot.source_system_ref"),
        },
        "policy": normalize_policy(p.get("policy")),
        "solution_packs": packs,
    }
    parse_utc(out["snapshot"]["captured_at"])
    return out


def snapshot_commitment(packet: Mapping[str, Any]) -> str:
    material = {
        "schema_version": packet["schema_version"],
        "snapshot": packet["snapshot"],
        "solution_packs": packet["solution_packs"],
    }
    return sha256_json(material)


def policy_commitment(packet: Mapping[str, Any]) -> str:
    return sha256_json(packet["policy"])


def _global_holds(packet: Mapping[str, Any], *, expected_snapshot_sha256: str, expected_policy_sha256: str, evaluation_time: str) -> list[str]:
    if not _hex64(expected_snapshot_sha256) or not _hex64(expected_policy_sha256):
        raise GateError("expected commitments must be lowercase sha256 hex")
    now = parse_utc(evaluation_time)
    captured = parse_utc(packet["snapshot"]["captured_at"])
    holds = []
    if snapshot_commitment(packet) != expected_snapshot_sha256:
        holds.append("SNAPSHOT_COMMITMENT_MISMATCH")
    if policy_commitment(packet) != expected_policy_sha256:
        holds.append("POLICY_COMMITMENT_MISMATCH")
    age = int((now - captured).total_seconds())
    if age < 0:
        holds.append("FUTURE_SNAPSHOT")
    elif age > packet["policy"]["max_snapshot_age_seconds"]:
        holds.append("STALE_SNAPSHOT")
    return sorted(holds)


def evaluate(packet: Any, *, expected_snapshot_sha256: str, expected_policy_sha256: str, evaluation_time: str) -> dict[str, Any]:
    n = normalize_packet(packet)
    p = n["policy"]
    ingredients = {x["ingredient_id"]: x for x in p["approved_ingredients"]}
    region_rules = {(x["ingredient_id"], x["region"], x["use_ref"], x["claim_ref"]): x for x in p["allowed_region_use_claims"]}
    legacy = {x["legacy_id"]: x for x in p["legacy_mappings"]}
    owners = {x["owner_ref"]: x for x in p["owners"]}
    global_holds = _global_holds(n, expected_snapshot_sha256=expected_snapshot_sha256, expected_policy_sha256=expected_policy_sha256, evaluation_time=evaluation_time)
    rows = []
    counts: dict[str, int] = {code: 0 for code in DEFECT_CODES}
    for pack in n["solution_packs"]:
        codes: list[str] = []
        ingredient = ingredients.get(pack["ingredient_id"])
        if ingredient is None or ingredient["spec_revision"] != pack["spec_revision"]:
            codes.append("SPEC_REVISION_MISMATCH")
        rule = region_rules.get((pack["ingredient_id"], pack["region"], pack["use_ref"], pack["claim_ref"]))
        if rule is None or pack["use_level_mgkg"] > rule["max_use_level_mgkg"]:
            codes.append("REGION_USE_CLAIM_MISMATCH")
        lm = legacy.get(pack["legacy_substitute"]["legacy_id"])
        if lm is None or lm["ingredient_id"] != pack["ingredient_id"] or lm["mapping_version"] != pack["legacy_substitute"]["mapping_version"] or not _hex64(pack["legacy_substitute"]["evidence_sha256"]):
            codes.append("LEGACY_MAPPING_MISMATCH")
        stability = pack["pilot_stability"]
        if stability["status"] != "PASS" or stability["protocol_version"] != p["stability_protocol_version"] or not _hex64(stability["evidence_sha256"]):
            codes.append("STABILITY_MISMATCH")
        commercial = owners.get(pack["commercial_owner_ref"])
        science = owners.get(pack["science_owner_ref"])
        if (
            commercial is None or commercial["role"] != "commercial" or
            science is None or science["role"] != "science" or
            pack["owner_version"] != p["owner_registry_version"] or
            commercial["owner_version"] != p["owner_registry_version"] or
            science["owner_version"] != p["owner_registry_version"]
        ):
            codes.append("OWNER_VERSION_MISMATCH")
        evidence_holds = []
        if not _hex64(pack["allergen_evidence_sha256"]):
            evidence_holds.append("ALLERGEN_EVIDENCE_MISSING")
        if not _hex64(pack["label_evidence_sha256"]):
            evidence_holds.append("LABEL_EVIDENCE_MISSING")
        if not _hex64(pack["source_sha256"]):
            evidence_holds.append("SOURCE_EVIDENCE_MISSING")
        codes = sorted(set(codes))
        for code in codes:
            counts[code] += 1
        all_holds = sorted(codes + evidence_holds + global_holds)
        rows.append({
            "record_id": pack["record_id"],
            "state": HOLD if all_holds else PASS,
            "codes": all_holds,
            "source_sha256": pack["source_sha256"],
            "evidence_sha256": {
                "allergen": pack["allergen_evidence_sha256"],
                "label": pack["label_evidence_sha256"],
                "legacy_mapping": pack["legacy_substitute"]["evidence_sha256"],
                "stability": pack["pilot_stability"]["evidence_sha256"],
            },
            "owners": {
                "commercial_owner_ref": pack["commercial_owner_ref"],
                "science_owner_ref": pack["science_owner_ref"],
                "owner_version": pack["owner_version"],
            },
        })
    summary = {
        "record_count": len(rows),
        "pass_count": sum(1 for row in rows if row["state"] == PASS),
        "hold_count": sum(1 for row in rows if row["state"] == HOLD),
        "seeded_defect_code_count": sum(counts.values()),
        "defect_code_counts": counts,
        "global_holds": global_holds,
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "decision": PASS if summary["hold_count"] == 0 else HOLD,
        "snapshot_id": n["snapshot"]["snapshot_id"],
        "evaluation_time": evaluation_time,
        "snapshot_commitment_sha256": snapshot_commitment(n),
        "policy_commitment_sha256": policy_commitment(n),
        "summary": summary,
        "rows": rows,
        "authority": {
            "formulation_authorized": False,
            "claim_approval_authorized": False,
            "regulatory_decision_authorized": False,
            "customer_promise_authorized": False,
            "product_release_authorized": False,
            "source_writes": 0,
            "network_writes": 0,
            "trusted_acquisition_proven_by_this_tool": False,
        },
    }
    return result


def evidence_manifest(result: Mapping[str, Any]) -> dict[str, Any]:
    records = []
    for row in result["rows"]:
        records.append({
            "record_id": row["record_id"],
            "source_sha256": row["source_sha256"],
            "evidence_sha256": row["evidence_sha256"],
            "owners": row["owners"],
            "codes": row["codes"],
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": result["snapshot_id"],
        "snapshot_commitment_sha256": result["snapshot_commitment_sha256"],
        "policy_commitment_sha256": result["policy_commitment_sha256"],
        "records": records,
    }


def render_markdown(result: Mapping[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "# Cross-Portfolio Formulation Evidence Gate",
        "",
        f"Overall decision: **{result['decision']}**",
        f"Records: {s['record_count']} · PASS: {s['pass_count']} · HOLD: {s['hold_count']}",
        f"Declared defect codes observed: {s['seeded_defect_code_count']}",
        "",
        "## Authority ceiling",
        "Read-only owner evidence review. No formulation, claim approval, regulatory decision, customer promise, or product release authority.",
        "",
        "## Rows",
        "",
        "| record | state | codes |",
        "|---|---|---|",
    ]
    for row in result["rows"]:
        lines.append(f"| `{row['record_id']}` | {row['state']} | {', '.join(row['codes']) or 'none'} |")
    return "\n".join(lines) + "\n"


def compile_artifacts(packet: Any, *, expected_snapshot_sha256: str, expected_policy_sha256: str, evaluation_time: str) -> dict[str, bytes]:
    result = evaluate(packet, expected_snapshot_sha256=expected_snapshot_sha256, expected_policy_sha256=expected_policy_sha256, evaluation_time=evaluation_time)
    result_bytes = canonical_json(result) + b"\n"
    manifest = evidence_manifest(result)
    manifest_bytes = canonical_json(manifest) + b"\n"
    report_bytes = render_markdown(result).encode("utf-8")
    receipt_base = {
        "schema_version": SCHEMA_VERSION,
        "source_packet_sha256": sha256_json(normalize_packet(packet)),
        "result_sha256": sha256_bytes(result_bytes),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "report_sha256": sha256_bytes(report_bytes),
        "snapshot_commitment_sha256": result["snapshot_commitment_sha256"],
        "policy_commitment_sha256": result["policy_commitment_sha256"],
        "evaluation_time": evaluation_time,
        "source_writes": 0,
        "network_writes": 0,
    }
    receipt = dict(receipt_base)
    receipt["receipt_sha256"] = sha256_json(receipt_base)
    return {
        "result.json": result_bytes,
        "evidence_manifest.json": manifest_bytes,
        "report.md": report_bytes,
        "receipt.json": canonical_json(receipt) + b"\n",
    }


def verify_artifacts(packet: Any, artifacts: Mapping[str, bytes], *, expected_snapshot_sha256: str, expected_policy_sha256: str, evaluation_time: str) -> bool:
    expected = compile_artifacts(packet, expected_snapshot_sha256=expected_snapshot_sha256, expected_policy_sha256=expected_policy_sha256, evaluation_time=evaluation_time)
    return set(artifacts) == set(expected) and all(artifacts[name] == expected[name] for name in expected)


def write_artifacts_exclusive(output_dir: str | os.PathLike[str], artifacts: Mapping[str, bytes]) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        for name in sorted(artifacts):
            path = out / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as fh:
                fh.write(artifacts[name])
            created.append(path)
    except Exception:
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        raise
