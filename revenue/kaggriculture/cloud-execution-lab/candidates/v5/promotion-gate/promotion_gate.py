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
from pathlib import Path
import re
import sys
import uuid
from collections.abc import Mapping
from typing import Any

SCHEMA = "titan-v5-promotion-gate/v1"
IDENTITY_SCHEMA = "titan-v5-candidate-identity/v1"
_V5C_RE = re.compile(r"^v5c:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
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


def validate_manifest(manifest: Mapping[str, Any]) -> str:
    """Validate the identity manifest's closed shape and self-authenticating ID."""
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
        if type(manifest[field]) is not str or not manifest[field].strip():
            raise PromotionError(f"candidate manifest {field} must be a non-empty string")
    opponent = manifest["opponent_pack_id"]
    if opponent is not None and (type(opponent) is not str or not opponent.strip()):
        raise PromotionError(
            "candidate manifest opponent_pack_id must be null or a non-empty string"
        )
    _hex64(manifest["config_sha256"], "candidate manifest config_sha256")
    if type(manifest["components"]) is not list:
        raise PromotionError("candidate manifest components must be a list")

    candidate_id = _v5c(manifest["candidate_id"], "candidate manifest candidate_id")
    body = {key: manifest[key] for key in manifest if key != "candidate_id"}
    expected = "v5c:" + _sha_value(body)
    if candidate_id != expected:
        raise PromotionError("candidate manifest candidate_id does not match manifest body")
    return candidate_id


def validate_engagement(report: Mapping[str, Any], candidate_id: str) -> str:
    """Require decision engagement for exactly the manifest candidate."""
    if type(report) is not dict:
        raise PromotionError("engagement report must be an object")
    control_id = _v5c(report.get("control_id"), "engagement control_id")
    engaged_id = _v5c(report.get("candidate_id"), "engagement candidate_id")
    if control_id == engaged_id:
        raise PromotionError("engagement control_id and candidate_id must differ")
    if engaged_id != candidate_id:
        raise PromotionError("engagement candidate_id does not match candidate manifest")
    if report.get("classification") != "ENGAGED":
        raise PromotionError("engagement classification must be ENGAGED")

    observations = _plain_int(report.get("observations"), "engagement observations", minimum=1)
    divergence = _plain_int(
        report.get("divergence_count"), "engagement divergence_count", minimum=1
    )
    if divergence > observations:
        raise PromotionError("engagement divergence_count exceeds observations")
    if not isinstance(report.get("first_divergence"), Mapping):
        raise PromotionError("ENGAGED report requires first_divergence")
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

    headroom = _finite_number(
        report.get("p99_headroom_seconds"), "runtime p99_headroom_seconds"
    )
    if headroom < 0:
        raise PromotionError("runtime p99 headroom must be nonnegative")


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
