from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import cv2
import numpy as np

SCHEMA = "opencv26-visual-evidence-gate/v1"
GENERATOR_VERSION = "synthetic-scene-v1"
DETECTOR_VERSION = "hsv-evidence-v1"
POLICY_VERSION = "evidence-action-policy-v1"
MAX_EVIDENCE_AGE_SECONDS = 30
REQUIRED_OPENCV_MAJOR = 5

ALLOWED_SCENARIOS = {
    "clear",
    "warning",
    "ambiguous",
    "stale_warning",
    "unsafe_requested_action",
}

SAFE_ACTION_CLASSES = {
    "OBSERVE_ONLY",
    "DIAGNOSTIC_RECHECK",
    "REQUEST_HUMAN_APPROVAL",
}

EXPECTED_TERMINAL_STATES = {
    "clear": "CONTINUE_MONITORING",
    "warning": "REQUEST_HUMAN_APPROVAL",
    "ambiguous": "REQUEST_HUMAN_APPROVAL",
    "stale_warning": "HOLD_STALE_EVIDENCE",
    "unsafe_requested_action": "HOLD_UNSAFE_ACTION_CLASS",
}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class GateError(ValueError):
    """Raised when the deterministic carrier cannot safely admit an input."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GateError(f"{field} must be an RFC3339 UTC string ending in Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GateError(f"{field} is not a real UTC instant") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise GateError(f"{field} must be UTC")
    return dt


def _fmt_utc(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _opencv_runtime(*, compatibility_mode: bool) -> dict[str, Any]:
    version = str(cv2.__version__)
    try:
        major = int(version.split(".", 1)[0])
    except (TypeError, ValueError) as exc:
        raise GateError("OpenCV runtime version is not parseable") from exc
    verified = major >= REQUIRED_OPENCV_MAJOR
    if not compatibility_mode and not verified:
        raise GateError(
            f"competition mode requires OpenCV {REQUIRED_OPENCV_MAJOR}+; runtime is {version}. "
            "Use compatibility_mode only for source-development evidence, never submission proof."
        )
    return {
        "runtime_version": version,
        "required_major": REQUIRED_OPENCV_MAJOR,
        "opencv5_verified": verified,
        "compatibility_mode": bool(compatibility_mode),
    }


def _scene_digest(image: np.ndarray) -> str:
    if not isinstance(image, np.ndarray):
        raise GateError("scene must be a numpy array")
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise GateError("scene must be uint8 HxWx3 BGR")
    h, w, _ = image.shape
    if h < 64 or w < 64 or h > 2048 or w > 2048:
        raise GateError("scene dimensions outside bounded carrier contract")
    return _sha256_bytes(image.tobytes(order="C"))


def generate_synthetic_scene(scenario: str) -> np.ndarray:
    """Generate a deterministic, rights-clean BGR scene from primitives only."""
    if scenario not in ALLOWED_SCENARIOS:
        raise GateError(f"unsupported synthetic scenario: {scenario!r}")

    image = np.full((256, 256, 3), 28, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (235, 235), (58, 58, 58), thickness=-1)
    cv2.rectangle(image, (45, 55), (210, 210), (85, 85, 85), thickness=-1)
    cv2.rectangle(image, (70, 90), (185, 175), (105, 105, 105), thickness=-1)
    cv2.circle(image, (128, 132), 26, (130, 130, 130), thickness=-1)

    cv2.rectangle(image, (54, 66), (78, 90), (32, 210, 32), thickness=-1)

    if scenario in {"warning", "stale_warning"}:
        cv2.rectangle(image, (164, 66), (204, 106), (25, 25, 240), thickness=-1)
    elif scenario == "ambiguous":
        cv2.rectangle(image, (168, 70), (190, 92), (20, 180, 235), thickness=-1)
    elif scenario == "unsafe_requested_action":
        cv2.rectangle(image, (165, 68), (181, 84), (20, 180, 235), thickness=-1)

    return image


def _color_fractions(image: np.ndarray) -> dict[str, float]:
    _scene_digest(image)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    red_low = cv2.inRange(hsv, np.array([0, 120, 120]), np.array([10, 255, 255]))
    red_high = cv2.inRange(hsv, np.array([170, 120, 120]), np.array([179, 255, 255]))
    red_mask = cv2.bitwise_or(red_low, red_high)
    amber_mask = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([40, 255, 255]))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    pixels = float(image.shape[0] * image.shape[1])
    return {
        "red_fraction": round(float(cv2.countNonZero(red_mask)) / pixels, 6),
        "amber_fraction": round(float(cv2.countNonZero(amber_mask)) / pixels, 6),
        "edge_fraction": round(float(cv2.countNonZero(edges)) / pixels, 6),
    }


def _perceive(image: np.ndarray, *, compatibility_mode: bool, scope: str) -> dict[str, Any]:
    runtime = _opencv_runtime(compatibility_mode=compatibility_mode)
    fractions = _color_fractions(image)
    return {
        "scope": scope,
        "scene_sha256": _scene_digest(image),
        "detector_version": DETECTOR_VERSION,
        "runtime": runtime,
        "measurements": fractions,
    }


def _decision_from_evidence(
    evidence: Mapping[str, Any],
    *,
    evidence_age_seconds: int,
    requested_action_class: str,
    recheck: bool,
) -> dict[str, Any]:
    if type(evidence_age_seconds) is not int or evidence_age_seconds < 0:
        raise GateError("evidence_age_seconds must be a nonnegative integer")
    if not isinstance(requested_action_class, str):
        raise GateError("requested_action_class must be text")

    if requested_action_class not in SAFE_ACTION_CLASSES:
        return {
            "state": "HOLD_UNSAFE_ACTION_CLASS",
            "next_tool": None,
            "human_control_required": True,
            "reason_codes": ["UNSAFE_ACTION_CLASS"],
        }
    if evidence_age_seconds > MAX_EVIDENCE_AGE_SECONDS:
        return {
            "state": "HOLD_STALE_EVIDENCE",
            "next_tool": None,
            "human_control_required": True,
            "reason_codes": ["STALE_VISUAL_EVIDENCE"],
        }

    measurements = evidence.get("measurements")
    if not isinstance(measurements, Mapping):
        raise GateError("evidence measurements missing")
    red = measurements.get("red_fraction")
    amber = measurements.get("amber_fraction")
    if not isinstance(red, (int, float)) or not math.isfinite(float(red)):
        raise GateError("red_fraction malformed")
    if not isinstance(amber, (int, float)) or not math.isfinite(float(amber)):
        raise GateError("amber_fraction malformed")

    if float(red) >= 0.008:
        return {
            "state": "REQUEST_HUMAN_APPROVAL",
            "next_tool": None,
            "human_control_required": True,
            "reason_codes": ["RED_WARNING_EVIDENCE"],
        }

    if float(amber) >= (0.003 if not recheck else 0.01):
        if not recheck:
            return {
                "state": "RUN_TARGETED_RECHECK",
                "next_tool": "opencv_targeted_roi_recheck",
                "human_control_required": False,
                "reason_codes": ["AMBER_AMBIGUITY"],
            }
        return {
            "state": "REQUEST_HUMAN_APPROVAL",
            "next_tool": None,
            "human_control_required": True,
            "reason_codes": ["AMBER_CONFIRMED_BY_RECHECK"],
        }

    return {
        "state": "CONTINUE_MONITORING",
        "next_tool": None,
        "human_control_required": False,
        "reason_codes": ["NO_ACTIONABLE_VISUAL_EVIDENCE"],
    }


def _targeted_recheck(image: np.ndarray, *, compatibility_mode: bool) -> dict[str, Any]:
    _scene_digest(image)
    roi = image[52:116, 150:216]
    if roi.size == 0:
        raise GateError("targeted ROI is empty")
    return _perceive(roi, compatibility_mode=compatibility_mode, scope="targeted_roi")


def _scenario_action_class(scenario: str) -> str:
    if scenario == "unsafe_requested_action":
        return "AUTONOMOUS_PHYSICAL_ACTUATION"
    return "OBSERVE_ONLY"


def compile_synthetic_run(
    scenario: str,
    *,
    evaluated_at: str = "2026-09-17T08:00:00Z",
    compatibility_mode: bool = True,
) -> dict[str, Any]:
    if scenario not in ALLOWED_SCENARIOS:
        raise GateError(f"unsupported synthetic scenario: {scenario!r}")
    evaluation_time = _parse_utc(evaluated_at, "evaluated_at")
    age = 120 if scenario == "stale_warning" else 0
    captured_time = evaluation_time - timedelta(seconds=age)
    requested_action = _scenario_action_class(scenario)
    image = generate_synthetic_scene(scenario)

    first = _perceive(image, compatibility_mode=compatibility_mode, scope="full_frame")
    first_decision = _decision_from_evidence(
        first,
        evidence_age_seconds=age,
        requested_action_class=requested_action,
        recheck=False,
    )

    steps: list[dict[str, Any]] = [
        {"step": 1, "tool": "opencv_full_frame_perception", "evidence": first, "decision": first_decision}
    ]
    terminal = first_decision

    if first_decision["state"] == "RUN_TARGETED_RECHECK":
        second = _targeted_recheck(image, compatibility_mode=compatibility_mode)
        second_decision = _decision_from_evidence(
            second,
            evidence_age_seconds=age,
            requested_action_class="DIAGNOSTIC_RECHECK",
            recheck=True,
        )
        steps.append(
            {"step": 2, "tool": "opencv_targeted_roi_recheck", "evidence": second, "decision": second_decision}
        )
        terminal = second_decision

    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "generator_version": GENERATOR_VERSION,
        "policy_version": POLICY_VERSION,
        "scenario": scenario,
        "captured_at": _fmt_utc(captured_time),
        "evaluated_at": _fmt_utc(evaluation_time),
        "evidence_age_seconds": age,
        "requested_action_class": requested_action,
        "steps": steps,
        "terminal": terminal,
        "authority": {
            "synthetic_fixture_only": True,
            "production_actuation_authorized": False,
            "camera_or_customer_data_authorized": False,
            "aws_deployment_verified": False,
            "devpost_submission_authorized": False,
            "prize_or_payment_claimed": False,
            "revenue_recognition_authorized": False,
        },
    }
    packet["receipt_sha256"] = _sha256_json(packet)
    return packet


def verify_trace(packet: Mapping[str, Any]) -> bool:
    if not isinstance(packet, Mapping):
        return False
    try:
        supplied = dict(packet)
        digest = supplied.pop("receipt_sha256")
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            return False
        if _sha256_json(supplied) != digest:
            return False
        if supplied.get("schema") != SCHEMA:
            return False
        scenario = supplied.get("scenario")
        evaluated_at = supplied.get("evaluated_at")
        if not isinstance(scenario, str) or not isinstance(evaluated_at, str):
            return False
        steps = supplied.get("steps")
        if not isinstance(steps, list) or not steps:
            return False
        runtime = steps[0].get("evidence", {}).get("runtime", {})
        compatibility_mode = runtime.get("compatibility_mode")
        if type(compatibility_mode) is not bool:
            return False
        rebuilt = compile_synthetic_run(
            scenario,
            evaluated_at=evaluated_at,
            compatibility_mode=compatibility_mode,
        )
        return rebuilt == dict(packet)
    except (GateError, KeyError, TypeError, ValueError):
        return False


def evaluate_synthetic_suite(
    *,
    evaluated_at: str = "2026-09-17T08:00:00Z",
    compatibility_mode: bool = True,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passed = 0
    for scenario in sorted(EXPECTED_TERMINAL_STATES):
        trace = compile_synthetic_run(
            scenario,
            evaluated_at=evaluated_at,
            compatibility_mode=compatibility_mode,
        )
        observed = trace["terminal"]["state"]
        expected = EXPECTED_TERMINAL_STATES[scenario]
        ok = observed == expected and verify_trace(trace)
        passed += int(ok)
        rows.append(
            {
                "scenario": scenario,
                "expected": expected,
                "observed": observed,
                "trace_receipt_sha256": trace["receipt_sha256"],
                "pass": bool(ok),
            }
        )

    total = len(rows)
    report: dict[str, Any] = {
        "schema": "opencv26-visual-evidence-evaluation/v1",
        "evaluated_at": evaluated_at,
        "compatibility_mode": bool(compatibility_mode),
        "cases": rows,
        "passed": passed,
        "total": total,
        "success_basis_points": (passed * 10000) // total,
        "all_expected_behaviors_observed": passed == total,
        "competition_evidence_ceiling": "LOCAL_SYNTHETIC_SOURCE_DEVELOPMENT_ONLY",
        "official_score_or_rank_claimed": False,
    }
    report["receipt_sha256"] = _sha256_json(report)
    return report
