"""Read-only AWS S3 manifest adapter for packet-quality.

The adapter constrains object identity and binds bytes before invoking the core.
It does not write to AWS and does not claim AWS execution merely because an
AWS-shaped event was supplied. A live deployment must retain provider evidence
separately.
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable, Mapping

from packet_quality import PacketQualityError, canonical_bytes, compile_triage, sha256, strict_json_bytes

BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+=,@-]{0,1023}$")
ETAG_RE = re.compile(r'^(?:"[0-9a-f]{32}(?:-\d+)?"|[0-9a-f]{32}(?:-\d+)?)$')


def _safe_key(value: Any, label: str) -> str:
    if type(value) is not str or not KEY_RE.fullmatch(value):
        raise PacketQualityError(f"{label}: invalid S3 key")
    if value.startswith("/") or ".." in value.split("/") or "//" in value:
        raise PacketQualityError(f"{label}: noncanonical S3 key")
    return value


def _bucket(value: Any) -> str:
    if type(value) is not str or not BUCKET_RE.fullmatch(value) or ".." in value:
        raise PacketQualityError("invalid S3 bucket")
    return value


def _etag(value: Any, label: str) -> str:
    if type(value) is not str or not ETAG_RE.fullmatch(value):
        raise PacketQualityError(f"{label}: canonical ETag required")
    return value.strip('"')


def compile_s3_manifest_event(event: Mapping[str, Any], s3_get: Callable[[str, str, str], bytes]) -> dict[str, Any]:
    if type(event) is not dict or set(event) != {"bucket", "manifest_key", "manifest_etag"}:
        raise PacketQualityError("event must contain exactly bucket, manifest_key, manifest_etag")
    bucket = _bucket(event["bucket"])
    manifest_key = _safe_key(event["manifest_key"], "manifest_key")
    manifest_etag = _etag(event["manifest_etag"], "manifest_etag")
    manifest_bytes = s3_get(bucket, manifest_key, manifest_etag)
    if not isinstance(manifest_bytes, (bytes, bytearray)):
        raise PacketQualityError("s3_get must return bytes")
    manifest = strict_json_bytes(bytes(manifest_bytes))
    if type(manifest) is not dict or set(manifest) != {"packet", "objects"}:
        raise PacketQualityError("manifest must contain exactly packet and objects")
    if type(manifest["packet"]) is not dict:
        raise PacketQualityError("manifest.packet must be object")
    if type(manifest["objects"]) is not list:
        raise PacketQualityError("manifest.objects must be list")
    bindings: dict[str, tuple[str, str, str]] = {}
    for i, row in enumerate(manifest["objects"]):
        if type(row) is not dict or set(row) != {"image_id", "key", "etag", "payload_sha256"}:
            raise PacketQualityError(f"manifest.objects[{i}] shape invalid")
        image_id = row["image_id"]
        if type(image_id) is not str or image_id in bindings:
            raise PacketQualityError("duplicate/invalid manifest image_id")
        key = _safe_key(row["key"], f"objects[{i}].key")
        etag = _etag(row["etag"], f"objects[{i}].etag")
        payload_sha = row["payload_sha256"]
        if type(payload_sha) is not str or len(payload_sha) != 64 or any(c not in "0123456789abcdef" for c in payload_sha):
            raise PacketQualityError("invalid manifest payload_sha256")
        bindings[image_id] = (key, etag, payload_sha)
    packet_ids = {row["image_id"] for row in manifest["packet"].get("images", []) if type(row) is dict and "image_id" in row}
    if packet_ids != set(bindings):
        raise PacketQualityError("manifest object set must exactly equal packet image ids")
    cache: dict[str, bytes] = {}
    def loader(image_id: str) -> bytes:
        if image_id not in bindings:
            raise PacketQualityError("unbound image id")
        if image_id not in cache:
            key, etag, payload_sha = bindings[image_id]
            payload = s3_get(bucket, key, etag)
            if not isinstance(payload, (bytes, bytearray)):
                raise PacketQualityError("s3_get must return bytes")
            data = bytes(payload)
            if sha256(data) != payload_sha:
                raise PacketQualityError("S3 object digest mismatch")
            cache[image_id] = data
        return cache[image_id]
    artifact = compile_triage(manifest["packet"], loader)
    envelope = {
        "adapter": "aws-s3-manifest-readonly/v1",
        "bucket": bucket,
        "manifest_key": manifest_key,
        "manifest_etag": manifest_etag,
        "manifest_sha256": sha256(bytes(manifest_bytes)),
        "aws_execution_proven": False,
    }
    core = {"adapter_schema": "visual-evidence-packet-quality-s3-artifact/v1", "core_artifact": artifact, "runtime_envelope": envelope}
    return {**core, "adapter_receipt_sha256": sha256(core)}


def verify_s3_manifest_event(event: Mapping[str, Any], s3_get: Callable[[str, str, str], bytes], artifact: Mapping[str, Any]) -> bool:
    """Verify adapter and outer runtime envelope by exact deterministic recompile."""
    if type(artifact) is not dict:
        raise PacketQualityError("adapter artifact must be plain object")
    expected = compile_s3_manifest_event(event, s3_get)
    try:
        actual_bytes = canonical_bytes(artifact)
        expected_bytes = canonical_bytes(expected)
    except (TypeError, ValueError) as exc:
        raise PacketQualityError("adapter artifact must contain plain canonical JSON values") from exc
    if actual_bytes != expected_bytes:
        raise PacketQualityError("adapter artifact does not exactly match deterministic recompile")
    receipt = artifact.get("adapter_receipt_sha256")
    if type(receipt) is not str or len(receipt) != 64 or any(c not in "0123456789abcdef" for c in receipt):
        raise PacketQualityError("adapter receipt malformed")
    core = {"adapter_schema": artifact.get("adapter_schema"), "core_artifact": artifact.get("core_artifact"), "runtime_envelope": artifact.get("runtime_envelope")}
    if sha256(core) != receipt:
        raise PacketQualityError("adapter receipt mismatch")
    return True


def lambda_handler(event: Mapping[str, Any], context: Any = None) -> dict[str, Any]:
    """Optional read-only deployment entry point; no AWS writes."""
    import cv2
    if not str(cv2.__version__).startswith("5."):
        raise PacketQualityError("live competition adapter requires OpenCV 5.x")
    if not os.environ.get("AWS_EXECUTION_ENV"):
        raise PacketQualityError("AWS execution environment evidence absent")
    import boto3
    client = boto3.client("s3")
    def s3_get(bucket: str, key: str, etag: str) -> bytes:
        response = client.get_object(Bucket=bucket, Key=key)
        actual = str(response.get("ETag", "")).strip('"')
        if actual != etag:
            raise PacketQualityError("provider ETag mismatch")
        body = response["Body"].read()
        if not isinstance(body, bytes):
            raise PacketQualityError("provider body must be bytes")
        return body
    return compile_s3_manifest_event(event, s3_get)
