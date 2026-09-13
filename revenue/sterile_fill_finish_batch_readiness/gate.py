from __future__ import annotations

import copy
import hashlib
from typing import Any

from ._common import (
    HOLD_STATUS, READY_STATUS, SCHEMA_VERSION, ReadinessError, _exact_keys, _fail,
    _object, _timestamp, canonical_json, sha256_json,
)
from ._evaluate import _authority_envelope, _evaluate, _summary
from ._normalize import _normalize_input

def compile_readiness(raw: Any, *, as_of: str) -> dict[str, Any]:
    as_of_canonical, _ = _timestamp(as_of, "asOf")
    payload = _normalize_input(copy.deepcopy(raw))
    holds, snapshot = _evaluate(payload, as_of_canonical)
    status = HOLD_STATUS if holds else READY_STATUS
    payload_digest = sha256_json(payload)
    policy = payload["policy"]
    batch_ref = hashlib.sha256(f"{policy['batchId']}|{policy['lotId']}|{policy['productCode']}".encode("utf-8")).hexdigest()[:24]
    receipt = {
        "schemaVersion": SCHEMA_VERSION, "status": status, "batchRef": batch_ref, "asOf": as_of_canonical,
        "eventCount": snapshot["eventCount"], "eventDigest": snapshot["eventDigest"],
        "policyDigest": snapshot["policyDigest"], "payloadDigest": payload_digest, "holds": holds,
        "sourceTrust": "OWNER_ASSERTED_SYNTHETIC_OR_EXTERNAL_EVIDENCE_POINTERS_ONLY",
        "authorities": _authority_envelope(),
    }
    return {"payload": payload, "receipt": receipt, "summaryMarkdown": _summary(receipt)}


def verify_readiness_package(package: Any) -> dict[str, Any]:
    root = _object(package, "PACKAGE_OBJECT_REQUIRED")
    _exact_keys(root, {"payload", "receipt", "summaryMarkdown"}, "PACKAGE_SHAPE_MISMATCH")
    receipt = _object(root["receipt"], "RECEIPT_OBJECT_REQUIRED")
    _exact_keys(receipt, {"schemaVersion", "status", "batchRef", "asOf", "eventCount", "eventDigest", "policyDigest", "payloadDigest", "holds", "sourceTrust", "authorities"}, "RECEIPT_SHAPE_MISMATCH")
    if receipt["schemaVersion"] != SCHEMA_VERSION:
        _fail("SCHEMA_VERSION_MISMATCH")
    rebuilt = compile_readiness(root["payload"], as_of=receipt["asOf"])
    if canonical_json(root["payload"]) != canonical_json(rebuilt["payload"]):
        _fail("PAYLOAD_MISMATCH")
    if canonical_json(receipt) != canonical_json(rebuilt["receipt"]):
        _fail("RECEIPT_MISMATCH")
    if root["summaryMarkdown"] != rebuilt["summaryMarkdown"]:
        _fail("SUMMARY_MISMATCH")
    return {"valid": True, "status": rebuilt["receipt"]["status"], "payloadDigest": rebuilt["receipt"]["payloadDigest"], "batchRef": rebuilt["receipt"]["batchRef"]}
