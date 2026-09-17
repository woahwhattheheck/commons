#!/usr/bin/env python3
"""Deterministic multi-photo visual evidence packet quality gate.

The core measures image bytes with OpenCV and compiles a bounded next action.
It never authorizes an external/business action and never treats vision as a
claim, compliance, fraud, payment, competition, or revenue decision.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Callable, Mapping, Sequence

import cv2
import numpy as np

SCHEMA = "visual-evidence-packet-quality/v1"
ARTIFACT_SCHEMA = "visual-evidence-packet-quality-artifact/v1"
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 50_000_000
MIN_EDGE = 32
MAX_EDGE = 8192
MIN_FOCUS_VARIANCE = 60.0
MAX_CLIPPED_FRACTION = 0.35
NEAR_DUPLICATE_DHASH_DISTANCE = 3
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ACTIONS = {
    "ACCEPT_FOR_HUMAN_REVIEW",
    "REQUEST_RECAPTURE",
    "REQUEST_MISSING_VIEW",
    "HOLD_DUPLICATE_EVIDENCE",
    "HOLD_UNSAFE_OR_UNREADABLE",
}
AUTHORITY = {
    "external_action_authorized": False,
    "claim_approved": False,
    "payment_authorized": False,
    "fraud_proven": False,
    "compliance_proven": False,
    "aws_execution_proven": False,
    "submission_proven": False,
    "prize_proven": False,
    "revenue_recognized": False,
}


class PacketQualityError(ValueError):
    pass


def _pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PacketQualityError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _bad_constant(value: str) -> None:
    raise PacketQualityError(f"non-finite JSON constant forbidden: {value}")


def _plain(value: Any, path: str = "$") -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise PacketQualityError(f"{path}: non-finite number")
        return
    if type(value) is list:
        for i, item in enumerate(value):
            _plain(item, f"{path}[{i}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise PacketQualityError(f"{path}: non-string key")
            _plain(item, f"{path}.{key}")
        return
    raise PacketQualityError(f"{path}: plain JSON types required")


def canonical_bytes(value: Any) -> bytes:
    _plain(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def sha256(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return hashlib.sha256(bytes(value)).hexdigest()
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def strict_json_bytes(raw: bytes, *, max_bytes: int = 1_048_576) -> Any:
    if len(raw) > max_bytes:
        raise PacketQualityError("JSON exceeds byte limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise PacketQualityError("JSON must be UTF-8") from exc
    value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    _plain(value)
    return value


def _ident(value: Any, label: str) -> str:
    if type(value) is not str or not ID_RE.fullmatch(value):
        raise PacketQualityError(f"{label}: canonical lowercase ASCII id required")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        raise PacketQualityError(f"{label}: lowercase sha256 required")
    return value


def _keys(obj: Mapping[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    missing = required - set(obj)
    unknown = set(obj) - allowed
    if missing:
        raise PacketQualityError(f"{label}: missing keys {sorted(missing)}")
    if unknown:
        raise PacketQualityError(f"{label}: unknown keys {sorted(unknown)}")


def _freeze(value: Any) -> Any:
    return json.loads(canonical_bytes(value), object_pairs_hook=_pairs, parse_constant=_bad_constant)


def _dhash(gray: np.ndarray) -> str:
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    bits = 0
    for bit in diff.flatten().tolist():
        bits = (bits << 1) | int(bool(bit))
    return f"{bits:016x}"


def _hamming_hex(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def _descriptor(gray: np.ndarray) -> str:
    tiny = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
    quantized = (tiny // 16).astype(np.uint8)
    return hashlib.sha256(quantized.tobytes()).hexdigest()


def measure_image_bytes(image_id: str, payload: bytes) -> dict[str, Any]:
    _ident(image_id, "image_id")
    if not isinstance(payload, (bytes, bytearray)):
        raise PacketQualityError("image payload must be bytes")
    data = bytes(payload)
    payload_sha = sha256(data)
    if not data or len(data) > MAX_IMAGE_BYTES:
        return {
            "image_id": image_id,
            "payload_sha256": payload_sha,
            "status": "UNREADABLE",
            "reason": "EMPTY_OR_OVERSIZE_BYTES",
        }
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        return {
            "image_id": image_id,
            "payload_sha256": payload_sha,
            "status": "UNREADABLE",
            "reason": "OPENCV_DECODE_FAILED",
        }
    height, width = int(image.shape[0]), int(image.shape[1])
    if height < MIN_EDGE or width < MIN_EDGE or height > MAX_EDGE or width > MAX_EDGE or height * width > MAX_PIXELS:
        return {
            "image_id": image_id,
            "payload_sha256": payload_sha,
            "status": "UNREADABLE",
            "reason": "UNSUPPORTED_DIMENSIONS",
            "width": width,
            "height": height,
        }
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    focus = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    low_clip = float(np.mean(gray <= 5))
    high_clip = float(np.mean(gray >= 250))
    mean_luma = float(np.mean(gray))
    return {
        "image_id": image_id,
        "payload_sha256": payload_sha,
        "status": "MEASURED",
        "width": width,
        "height": height,
        "focus_variance": round(focus, 6),
        "low_clip_fraction": round(low_clip, 6),
        "high_clip_fraction": round(high_clip, 6),
        "mean_luminance": round(mean_luma, 6),
        "dhash64": _dhash(gray),
        "visual_descriptor_sha256": _descriptor(gray),
    }


def _validate_packet(packet: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if type(packet) is not dict:
        raise PacketQualityError("packet must be object")
    _plain(packet)
    _keys(packet, {"schema", "packet_id", "required_slots", "images"}, {"schema", "packet_id", "required_slots", "images"}, "packet")
    if packet["schema"] != SCHEMA:
        raise PacketQualityError("unsupported packet schema")
    _ident(packet["packet_id"], "packet.packet_id")
    if type(packet["required_slots"]) is not list or type(packet["images"]) is not list:
        raise PacketQualityError("required_slots/images must be lists")
    slots: list[dict[str, str]] = []
    seen_slots: set[str] = set()
    for i, raw in enumerate(packet["required_slots"]):
        if type(raw) is not dict:
            raise PacketQualityError(f"required_slots[{i}] must be object")
        _keys(raw, {"slot_id", "label"}, {"slot_id", "label"}, f"required_slots[{i}]")
        slot_id = _ident(raw["slot_id"], f"required_slots[{i}].slot_id")
        label = _ident(raw["label"], f"required_slots[{i}].label")
        if slot_id in seen_slots:
            raise PacketQualityError("duplicate slot_id")
        seen_slots.add(slot_id)
        slots.append({"slot_id": slot_id, "label": label})
    if [s["slot_id"] for s in slots] != sorted(s["slot_id"] for s in slots):
        raise PacketQualityError("required_slots must be sorted by slot_id")
    images: list[dict[str, str]] = []
    seen_images: set[str] = set()
    seen_image_slots: set[str] = set()
    for i, raw in enumerate(packet["images"]):
        if type(raw) is not dict:
            raise PacketQualityError(f"images[{i}] must be object")
        _keys(raw, {"image_id", "slot_id", "payload_sha256"}, {"image_id", "slot_id", "payload_sha256"}, f"images[{i}]")
        image_id = _ident(raw["image_id"], f"images[{i}].image_id")
        slot_id = _ident(raw["slot_id"], f"images[{i}].slot_id")
        payload_sha = _sha(raw["payload_sha256"], f"images[{i}].payload_sha256")
        if slot_id not in seen_slots:
            raise PacketQualityError("image targets unknown slot")
        if image_id in seen_images:
            raise PacketQualityError("duplicate image_id")
        if slot_id in seen_image_slots:
            raise PacketQualityError("multiple images for one slot are ambiguous")
        seen_images.add(image_id)
        seen_image_slots.add(slot_id)
        images.append({"image_id": image_id, "slot_id": slot_id, "payload_sha256": payload_sha})
    if [(x["slot_id"], x["image_id"]) for x in images] != sorted((x["slot_id"], x["image_id"]) for x in images):
        raise PacketQualityError("images must be sorted by slot_id,image_id")
    return slots, images


def compile_triage(packet: Mapping[str, Any], image_loader: Callable[[str], bytes]) -> dict[str, Any]:
    frozen = _freeze(packet)
    slots, images = _validate_packet(frozen)
    measurements: list[dict[str, Any]] = []
    by_slot: dict[str, dict[str, Any]] = {}
    for item in images:
        payload = image_loader(item["image_id"])
        if not isinstance(payload, (bytes, bytearray)):
            raise PacketQualityError("image_loader must return bytes")
        if sha256(bytes(payload)) != item["payload_sha256"]:
            raise PacketQualityError(f"payload digest mismatch: {item['image_id']}")
        measurement = measure_image_bytes(item["image_id"], bytes(payload))
        record = {"slot_id": item["slot_id"], **measurement}
        measurements.append(record)
        by_slot[item["slot_id"]] = record

    action = "ACCEPT_FOR_HUMAN_REVIEW"
    reasons: list[dict[str, str]] = []
    affected_slots: list[str] = []

    unreadable = [m for m in measurements if m["status"] != "MEASURED"]
    if unreadable:
        action = "HOLD_UNSAFE_OR_UNREADABLE"
        for m in unreadable:
            reasons.append({"code": "UNREADABLE_IMAGE", "detail": m["reason"], "slot_id": m["slot_id"]})
            affected_slots.append(m["slot_id"])

    if action == "ACCEPT_FOR_HUMAN_REVIEW":
        duplicates: list[tuple[str, str, str]] = []
        for i, left in enumerate(measurements):
            for right in measurements[i + 1:]:
                if left["payload_sha256"] == right["payload_sha256"]:
                    duplicates.append((left["slot_id"], right["slot_id"], "EXACT_DUPLICATE"))
                elif _hamming_hex(left["dhash64"], right["dhash64"]) <= NEAR_DUPLICATE_DHASH_DISTANCE:
                    duplicates.append((left["slot_id"], right["slot_id"], "NEAR_DUPLICATE"))
        if duplicates:
            action = "HOLD_DUPLICATE_EVIDENCE"
            for a, b, kind in duplicates:
                reasons.append({"code": kind, "detail": f"{a}<->{b}", "slot_id": a})
                affected_slots.extend([a, b])

    if action == "ACCEPT_FOR_HUMAN_REVIEW":
        missing = [s for s in slots if s["slot_id"] not in by_slot]
        if missing:
            action = "REQUEST_MISSING_VIEW"
            for slot in missing:
                reasons.append({"code": "MISSING_REQUIRED_SLOT", "detail": slot["label"], "slot_id": slot["slot_id"]})
                affected_slots.append(slot["slot_id"])

    if action == "ACCEPT_FOR_HUMAN_REVIEW":
        poor: list[tuple[dict[str, Any], str]] = []
        for m in measurements:
            if m["focus_variance"] < MIN_FOCUS_VARIANCE:
                poor.append((m, "LOW_FOCUS"))
            elif m["low_clip_fraction"] > MAX_CLIPPED_FRACTION:
                poor.append((m, "SHADOW_CLIPPING"))
            elif m["high_clip_fraction"] > MAX_CLIPPED_FRACTION:
                poor.append((m, "HIGHLIGHT_CLIPPING"))
        if poor:
            action = "REQUEST_RECAPTURE"
            for m, code in poor:
                reasons.append({"code": code, "detail": "measured quality below code-owned evidence floor", "slot_id": m["slot_id"]})
                affected_slots.append(m["slot_id"])

    affected_slots = sorted(set(affected_slots))
    if action not in ACTIONS:
        raise PacketQualityError("internal action outside code-owned enum")
    measurement_set = {
        "packet_sha256": sha256(frozen),
        "measurements": measurements,
        "thresholds": {
            "min_focus_variance": MIN_FOCUS_VARIANCE,
            "max_clipped_fraction": MAX_CLIPPED_FRACTION,
            "near_duplicate_dhash_distance": NEAR_DUPLICATE_DHASH_DISTANCE,
        },
    }
    measurement_receipt = sha256(measurement_set)
    trace = {
        "action": action,
        "reasons": reasons,
        "affected_slots": affected_slots,
        "measurement_receipt_sha256": measurement_receipt,
        "vision_changed_next_step": action != "ACCEPT_FOR_HUMAN_REVIEW",
        "human_boundary": "NO_SUBSTANTIVE_BUSINESS_DECISION; HUMAN_REVIEW_REQUIRED",
    }
    decision = {
        "packet_id": frozen["packet_id"],
        "packet_sha256": sha256(frozen),
        "opencv_runtime_observed": str(cv2.__version__),
        "measurements": measurements,
        "trace": trace,
        "authority": dict(AUTHORITY),
        "truth": {
            "image_bytes_measured_here": True,
            "provider_execution_authenticated_here": False,
            "aws_runtime_proven_here": False,
            "competition_submission_proven_here": False,
            "accept_for_human_review_is_business_approval": False,
        },
    }
    core = {"artifact_schema": ARTIFACT_SCHEMA, "decision": decision}
    return {**core, "receipt_sha256": sha256(core)}


def verify_triage(packet: Mapping[str, Any], image_loader: Callable[[str], bytes], artifact: Mapping[str, Any]) -> bool:
    frozen_artifact = _freeze(artifact)
    expected = compile_triage(packet, image_loader)
    if canonical_bytes(frozen_artifact) != canonical_bytes(expected):
        raise PacketQualityError("artifact does not match deterministic recompile")
    receipt = frozen_artifact.get("receipt_sha256")
    if type(receipt) is not str or not SHA_RE.fullmatch(receipt):
        raise PacketQualityError("malformed receipt")
    core = {"artifact_schema": frozen_artifact["artifact_schema"], "decision": frozen_artifact["decision"]}
    if sha256(core) != receipt:
        raise PacketQualityError("receipt mismatch")
    if any(frozen_artifact["decision"]["authority"].values()):
        raise PacketQualityError("authority ceiling violated")
    return True
