#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed cross-evidence promotion receipts for TITAN V5.

This module is deliberately outside the gameplay path. It binds the stable
candidate identity manifest, matched engagement evidence, and runtime-budget
admission report into one deterministic promotion receipt. A PASS proves only
that those evidence summaries are mutually consistent; it does not replace the
underlying source, engine, or simulation evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import uuid
from collections.abc import Mapping
from typing import Any

SCHEMA = "titan-v5-promotion-gate/v1"
IDENTITY_SCHEMA = "titan-v5-candidate-identity/v1"
_V5C_RE = re.compile(r"^v5c:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_INT_TEXT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
_MANIFEST_KEYS = frozenset(
    (
        "schema",
        "base_id",
        "engine_id",
        "opponent_pack_id",
        "config_sha256",
        "components",
        "candidate_id",
    )
)
_COMPONENT_KEYS = frozenset(("name", "source", "source_sha256", "activation"))
_ENGAGEMENT_KEYS = frozenset(
    (
        "classification",
        "observations",
        "noop_threshold",
        "divergence_count",
        "engagement_rate",
        "first_divergence",
        "control_sequence_fingerprint",
        "candidate_sequence_fingerprint",
        "key_fields",
        "control_id",
        "candidate_id",
    )
)
_DIVERGENCE_KEYS = frozenset(
    ("observation", "key", "control_fingerprint", "candidate_fingerprint")
)


class PromotionError(ValueError):
    """Promotion evidence is malformed, incomplete, or cross-wired."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha_value(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PromotionError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise PromotionError(f"non-finite JSON constant is forbidden: {token}")


def _loads_strict(text: str, *, source: str = "<memory>") -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise PromotionError(f"{source}: invalid JSON: {exc.msg}") from exc


def _load_json(path: Path) -> tuple[Any, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PromotionError(f"cannot read evidence file: {path}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PromotionError(f"evidence file is not UTF-8: {path}") from exc
    return _loads_strict(text, source=str(path)), hashlib.sha256(raw).hexdigest()


def _v5c(value: Any, field: str) -> str:
    if type(value) is not str or _V5C_RE.fullmatch(value) is None:
        raise PromotionError(f"{field} must be v5c:<64 lowercase hex>")
    return value


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or _HEX64_RE.fullmatch(value) is None:
        raise PromotionError(f"{field} must be 64 lowercase hex characters")
    return value


def _plain_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PromotionError(f"{field} must be a plain int >= {minimum}")
    return value


def _finite_number(value: Any, field: str, *, minimum: float | None = None) -> float:
    if type(value) not in (int, float):
        raise PromotionError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise PromotionError(f"{field} must be a finite number")
    if minimum is not None and result < minimum:
        raise PromotionError(f"{field} must be >= {minimum}")
    return result


def _nonempty_text(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise PromotionError(f"{field} must be a non-empty string")
    return value


def _validate_typed(value: Any, field: str) -> None:
    """Validate the exact type-preserving tree emitted by v5_candidate_identity."""
    if type(value) is not dict or "t" not in value:
        raise PromotionError(f"{field} must be a canonical typed identity value")
    tag = value.get("t")
    if type(tag) is not str:
        raise PromotionError(f"{field}.t must be a string")

    if tag == "none":
        if set(value) != {"t"}:
            raise PromotionError(f"{field} none value has noncanonical keys")
        return
    if set(value) != {"t", "v"}:
        raise PromotionError(f"{field} typed value has noncanonical keys")
    payload = value["v"]

    if tag == "bool":
        if type(payload) is not bool:
            raise PromotionError(f"{field} bool payload must be an exact bool")
        return
    if tag == "int":
        if type(payload) is not str or _INT_TEXT_RE.fullmatch(payload) is None:
            raise PromotionError(f"{field} int payload must be canonical decimal text")
        if str(int(payload)) != payload:
            raise PromotionError(f"{field} int payload is not canonical")
        return
    if tag == "float":
        if type(payload) is not str:
            raise PromotionError(f"{field} float payload must be canonical hex text")
        try:
            number = float.fromhex(payload)
        except ValueError as exc:
            raise PromotionError(f"{field} float payload is invalid") from exc
        if not math.isfinite(number) or number.hex() != payload:
            raise PromotionError(f"{field} float payload is not canonical finite hex")
        return
    if tag == "str":
        if type(payload) is not str:
            raise PromotionError(f"{field} string payload must be a string")
        return
    if tag == "list":
        if type(payload) is not list:
            raise PromotionError(f"{field} list payload must be a list")
        for index, item in enumerate(payload):
            _validate_typed(item, f"{field}.v[{index}]")
        return
    if tag == "dict":
        if type(payload) is not list:
            raise PromotionError(f"{field} dict payload must be a list of key/value pairs")
        keys: list[str] = []
        for index, pair in enumerate(payload):
            if type(pair) is not list or len(pair) != 2 or type(pair[0]) is not str:
                raise PromotionError(f"{field}.v[{index}] must be [string, typed-value]")
            keys.append(pair[0])
            _validate_typed(pair[1], f"{field}.v[{index}][1]")
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise PromotionError(f"{field} dict keys must be unique and sorted")
        return
    raise PromotionError(f"{field} has unsupported typed tag {tag!r}")


def _validate_component(component: Any, index: int) -> str:
    field = f"candidate manifest components[{index}]"
    if type(component) is not dict or set(component) != _COMPONENT_KEYS:
        raise PromotionError(f"{field} must have exact canonical component keys")
    name = _nonempty_text(component["name"], f"{field}.name")
    source = _nonempty_text(component["source"], f"{field}.source")
    path = PurePosixPath(source)
    if (
        path.is_absolute()
        or path.as_posix() != source
        or source == "."
        or any(part in (".", "..") for part in path.parts)
    ):
        raise PromotionError(f"{field}.source must be a canonical relative path")
    _hex64(component["source_sha256"], f"{field}.source_sha256")

    activation = component["activation"]
    if type(activation) is not dict:
        raise PromotionError(f"{field}.activation must be an object")
    mode = activation.get("mode")
    if mode == "unconditional":
        if set(activation) != {"mode"}:
            raise PromotionError(f"{field}.activation unconditional record is not canonical")
    elif mode == "config":
        if set(activation) != {"mode", "equals"}:
            raise PromotionError(f"{field}.activation config record is not canonical")
        _validate_typed(activation["equals"], f"{field}.activation.equals")
        if activation["equals"].get("t") != "dict":
            raise PromotionError(f"{field}.activation.equals must encode a config mapping")
    else:
        raise PromotionError(f"{field}.activation mode is not canonical")
    return name


def validate_manifest(manifest: Mapping[str, Any]) -> str:
    """Validate the identity manifest's closed canonical shape and self-authenticating ID."""
    if type(manifest) is not dict:
        raise PromotionError("candidate manifest must be an object")
    if set(manifest) != _MANIFEST_KEYS:
        missing = sorted(_MANIFEST_KEYS - set(manifest))
        extra = sorted(set(manifest) - _MANIFEST_KEYS)
        raise PromotionError(
            f"candidate manifest keys mismatch; missing={missing!r} extra={extra!r}"
        )
    if manifest["schema"] != IDENTITY_SCHEMA:
        raise PromotionError(f"candidate manifest schema must be {IDENTITY_SCHEMA}")
    for field in ("base_id", "engine_id"):
        _nonempty_text(manifest[field], f"candidate manifest {field}")
    opponent = manifest["opponent_pack_id"]
    if opponent is not None:
        _nonempty_text(opponent, "candidate manifest opponent_pack_id")
    _hex64(manifest["config_sha256"], "candidate manifest config_sha256")
    if type(manifest["components"]) is not list:
        raise PromotionError("candidate manifest components must be a list")
    names = [
        _validate_component(component, index)
        for index, component in enumerate(manifest["components"])
    ]
    if len(names) != len(set(names)):
        raise PromotionError("candidate manifest component names must be unique")
    if names != sorted(names):
        raise PromotionError("candidate manifest components must be sorted by name")

    candidate_id = _v5c(manifest["candidate_id"], "candidate manifest candidate_id")
    body = {key: manifest[key] for key in manifest if key != "candidate_id"}
    expected = "v5c:" + _sha_value(body)
    if candidate_id != expected:
        raise PromotionError("candidate manifest candidate_id does not match manifest body")
    return candidate_id


def validate_engagement(report: Mapping[str, Any], candidate_id: str) -> str:
    """Require a canonical identity-stamped engagement report for the manifest candidate."""
    if type(report) is not dict:
        raise PromotionError("engagement report must be an object")
    if set(report) != _ENGAGEMENT_KEYS:
        missing = sorted(_ENGAGEMENT_KEYS - set(report))
        extra = sorted(set(report) - _ENGAGEMENT_KEYS)
        raise PromotionError(
            f"engagement report keys mismatch; missing={missing!r} extra={extra!r}"
        )

    control_id = _v5c(report["control_id"], "engagement control_id")
    engaged_id = _v5c(report["candidate_id"], "engagement candidate_id")
    if control_id == engaged_id:
        raise PromotionError("engagement control_id and candidate_id must differ")
    if engaged_id != candidate_id:
        raise PromotionError("engagement candidate_id does not match candidate manifest")
    if report["classification"] != "ENGAGED":
        raise PromotionError("engagement classification must be ENGAGED")

    observations = _plain_int(report["observations"], "engagement observations", minimum=1)
    _plain_int(report["noop_threshold"], "engagement noop_threshold", minimum=1)
    divergence = _plain_int(
        report["divergence_count"], "engagement divergence_count", minimum=1
    )
    if divergence > observations:
        raise PromotionError("engagement divergence_count exceeds observations")
    rate = _finite_number(report["engagement_rate"], "engagement engagement_rate", minimum=0.0)
    expected_rate = divergence / observations
    if rate > 1.0 or not math.isclose(rate, expected_rate, rel_tol=0.0, abs_tol=1e-15):
        raise PromotionError("engagement rate disagrees with divergence count")

    key_fields = report["key_fields"]
    if (
        type(key_fields) is not list
        or not key_fields
        or any(type(field) is not str or not field for field in key_fields)
        or len(key_fields) != len(set(key_fields))
    ):
        raise PromotionError("engagement key_fields must be unique non-empty strings")
    _hex64(
        report["control_sequence_fingerprint"],
        "engagement control_sequence_fingerprint",
    )
    _hex64(
        report["candidate_sequence_fingerprint"],
        "engagement candidate_sequence_fingerprint",
    )

    first = report["first_divergence"]
    if type(first) is not dict or set(first) != _DIVERGENCE_KEYS:
        raise PromotionError("ENGAGED report requires canonical first_divergence")
    first_observation = _plain_int(
        first["observation"], "engagement first_divergence observation", minimum=1
    )
    if first_observation > observations:
        raise PromotionError("engagement first_divergence exceeds observations")
    key = first["key"]
    if type(key) is not dict or set(key) != set(key_fields):
        raise PromotionError("engagement first_divergence key must match key_fields")
    control_fp = _hex64(
        first["control_fingerprint"], "engagement first_divergence control_fingerprint"
    )
    candidate_fp = _hex64(
        first["candidate_fingerprint"], "engagement first_divergence candidate_fingerprint"
    )
    if control_fp == candidate_fp:
        raise PromotionError("engagement first_divergence fingerprints must differ")
    return control_id


def validate_runtime(report: Mapping[str, Any], candidate_id: str) -> None:
    """Require a complete, candidate-pure runtime admission PASS."""
    if type(report) is not dict:
        raise PromotionError("runtime report must be an object")
    if report.get("classification") != "PASS" or report.get("promotion_ready") is not True:
        raise PromotionError("runtime report must be PASS with promotion_ready=true")
    if report.get("expected_design_declared") is not True:
        raise PromotionError("runtime report must declare an expected callback design")
    if report.get("expected_complete") is not True:
        raise PromotionError("runtime report expected design is incomplete")
    if report.get("missing_expected") != []:
        raise PromotionError("runtime report contains missing expected callbacks")
    if report.get("unexpected_extra") != []:
        raise PromotionError("runtime report contains unexpected callbacks")

    receipt_count = _plain_int(report.get("receipt_count"), "runtime receipt_count", minimum=1)
    expected_count = _plain_int(
        report.get("expected_callback_count"), "runtime expected_callback_count", minimum=1
    )
    if expected_count != receipt_count:
        raise PromotionError("runtime expected_callback_count must equal receipt_count")
    if _plain_int(report.get("candidate_count"), "runtime candidate_count", minimum=1) != 1:
        raise PromotionError("runtime evidence must contain exactly one candidate")

    by_candidate = report.get("by_candidate")
    if type(by_candidate) is not dict or set(by_candidate) != {candidate_id}:
        raise PromotionError("runtime by_candidate must contain only the manifest candidate")
    candidate_summary = by_candidate[candidate_id]
    if type(candidate_summary) is not dict:
        raise PromotionError("runtime candidate summary must be an object")
    if _plain_int(
        candidate_summary.get("count"), "runtime candidate callback count", minimum=1
    ) != receipt_count:
        raise PromotionError("runtime candidate callback count must equal receipt_count")

    overall = report.get("overall")
    if type(overall) is not dict:
        raise PromotionError("runtime overall summary must be an object")
    if _plain_int(overall.get("count"), "runtime overall count", minimum=1) != receipt_count:
        raise PromotionError("runtime overall count must equal receipt_count")

    budget = _finite_number(report.get("budget_seconds"), "runtime budget_seconds", minimum=0.0)
    if budget <= 0:
        raise PromotionError("runtime budget_seconds must be > 0")
    reserve = _finite_number(
        report.get("reserve_seconds"), "runtime reserve_seconds", minimum=0.0
    )
    if reserve >= budget:
        raise PromotionError("runtime reserve_seconds must be < budget_seconds")
    usable = _finite_number(
        report.get("usable_budget_seconds"), "runtime usable_budget_seconds", minimum=0.0
    )
    expected_usable = budget - reserve
    if not math.isclose(usable, expected_usable, rel_tol=0.0, abs_tol=1e-15):
        raise PromotionError("runtime usable budget disagrees with budget and reserve")
    wall = overall.get("wall_seconds")
    if type(wall) is not dict:
        raise PromotionError("runtime overall wall_seconds must be an object")
    p99_wall = _finite_number(wall.get("p99"), "runtime overall p99 wall", minimum=0.0)
    headroom = _finite_number(
        report.get("p99_headroom_seconds"), "runtime p99_headroom_seconds"
    )
    expected_headroom = usable - p99_wall
    if not math.isclose(headroom, expected_headroom, rel_tol=0.0, abs_tol=1e-15):
        raise PromotionError("runtime p99 headroom disagrees with usable budget and p99 wall")
    if p99_wall > usable or headroom < 0:
        raise PromotionError("runtime p99 wall exceeds usable budget")

    fallback_count = _plain_int(
        report.get("deadline_fallback_count"), "runtime deadline_fallback_count"
    )
    if fallback_count > receipt_count:
        raise PromotionError("runtime deadline_fallback_count exceeds receipt_count")
    candidate_fallbacks = _plain_int(
        candidate_summary.get("deadline_fallback_count"),
        "runtime candidate deadline_fallback_count",
    )
    if candidate_fallbacks != fallback_count:
        raise PromotionError("runtime candidate fallback count disagrees with overall count")

    fallback_rate = _finite_number(
        report.get("deadline_fallback_rate"), "runtime deadline_fallback_rate", minimum=0.0
    )
    fallback_ceiling = _finite_number(
        report.get("max_fallback_rate"), "runtime max_fallback_rate", minimum=0.0
    )
    if fallback_rate > 1.0 or fallback_ceiling > 1.0:
        raise PromotionError("runtime fallback rates must be <= 1")
    expected_rate = fallback_count / receipt_count
    if not math.isclose(fallback_rate, expected_rate, rel_tol=0.0, abs_tol=1e-15):
        raise PromotionError("runtime fallback rate disagrees with fallback count")
    if fallback_rate > fallback_ceiling:
        raise PromotionError("runtime fallback rate exceeds declared ceiling")


def _evidence_hashes(
    manifest: Mapping[str, Any],
    engagement: Mapping[str, Any],
    runtime: Mapping[str, Any],
    supplied: Mapping[str, str] | None,
) -> dict[str, str]:
    if supplied is None:
        return {
            "candidate_manifest": _sha_value(manifest),
            "engagement_report": _sha_value(engagement),
            "runtime_report": _sha_value(runtime),
        }
    if type(supplied) is not dict or set(supplied) != {
        "candidate_manifest",
        "engagement_report",
        "runtime_report",
    }:
        raise PromotionError("evidence hashes must cover exactly all three evidence inputs")
    return {key: _hex64(value, f"evidence hash {key}") for key, value in supplied.items()}


def build_receipt(
    manifest: Mapping[str, Any],
    engagement: Mapping[str, Any],
    runtime: Mapping[str, Any],
    *,
    evidence_sha256: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a deterministic PASS receipt or raise PromotionError."""
    candidate_id = validate_manifest(manifest)
    control_id = validate_engagement(engagement, candidate_id)
    validate_runtime(runtime, candidate_id)
    hashes = _evidence_hashes(manifest, engagement, runtime, evidence_sha256)
    return {
        "schema": SCHEMA,
        "classification": "PASS",
        "promotion_ready": True,
        "candidate_id": candidate_id,
        "control_id": control_id,
        "evidence_sha256": hashes,
        "engagement": {
            "observations": engagement["observations"],
            "divergence_count": engagement["divergence_count"],
        },
        "runtime": {
            "receipt_count": runtime["receipt_count"],
            "deadline_fallback_count": runtime["deadline_fallback_count"],
            "deadline_fallback_rate": runtime["deadline_fallback_rate"],
            "p99_headroom_seconds": runtime["p99_headroom_seconds"],
        },
    }


def _emit(receipt: Mapping[str, Any], output: Path | None) -> None:
    payload = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ) + "\n"
    if output is None:
        print(payload, end="")
        return
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_manifest", type=Path)
    parser.add_argument("engagement_report", type=Path)
    parser.add_argument("runtime_report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest, manifest_sha = _load_json(args.candidate_manifest)
        engagement, engagement_sha = _load_json(args.engagement_report)
        runtime, runtime_sha = _load_json(args.runtime_report)
        receipt = build_receipt(
            manifest,
            engagement,
            runtime,
            evidence_sha256={
                "candidate_manifest": manifest_sha,
                "engagement_report": engagement_sha,
                "runtime_report": runtime_sha,
            },
        )
        _emit(receipt, args.output)
    except (PromotionError, OSError, TypeError, ValueError) as exc:
        print(f"promotion_gate: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
