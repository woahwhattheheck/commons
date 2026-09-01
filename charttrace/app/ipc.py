"""Retired filesystem-mailbox compatibility surface.

Lane C never used this transport from the product launcher or controller.
The prior mailbox implementation was not a defensible Windows boundary, so
all filesystem-facing APIs fail closed and the frozen application excludes
this module.  Only a pure, length-bounded JSON frame codec remains for
inspecting old synthetic fixtures without Python-object deserialization.
"""

import hashlib
import hmac
import json
import struct
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

MAGIC = b"CTJ1"
MAX_FRAME = 65_536
MAX_JSON_MESSAGE_BYTES = MAX_FRAME
PROTOCOL_VERSION = 1
ALLOWED_OPS: FrozenSet[str] = frozenset({"ping", "handoff", "status"})
REQUIRED_FIELDS = ("v", "op", "nonce", "mac")
TRANSPORT = "DISABLED_NOT_PRODUCT"
PRODUCT_IPC_ENABLED = False
IPC_REMOVAL_RECEIPT = "unused-filesystem-mailbox-retired-before-frozen-build"


class IpcProtocolError(ValueError):
    pass


JsonIpcError = IpcProtocolError


class IpcDisabledError(IpcProtocolError):
    """Raised whenever the retired filesystem transport is invoked."""


def _require_product_ipc_disabled() -> None:
    raise IpcDisabledError(
        "ChartTrace filesystem IPC was removed from the product boundary."
    )


def _reject_constant(value: str) -> None:
    raise IpcProtocolError(f"Non-finite JSON constant {value!r} is prohibited.")


def _unique_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IpcProtocolError(f"Duplicate JSON key {key!r} is prohibited.")
        result[key] = value
    return result


def decode_json_message(payload: bytes) -> Dict[str, Any]:
    if not payload or len(payload) > MAX_JSON_MESSAGE_BYTES:
        raise IpcProtocolError("JSON frame size is invalid.")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise IpcProtocolError("Frame must be valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise IpcProtocolError("Frame must be a JSON object.")
    return value


def encode_json_message(value: Dict[str, Any]) -> bytes:
    if not isinstance(value, dict):
        raise IpcProtocolError("Frame must be a JSON object.")
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise IpcProtocolError("Frame is not JSON serializable.") from error
    if len(payload) > MAX_JSON_MESSAGE_BYTES:
        raise IpcProtocolError("Frame is too large.")
    return payload


def sign_message(session_key: bytes, payload: Dict[str, Any]) -> str:
    body = json.dumps(
        {key: payload[key] for key in ("v", "op", "nonce") if key in payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(session_key, body, hashlib.sha256).hexdigest()


def encode_frame(payload: Dict[str, Any]) -> bytes:
    body = encode_json_message(payload)
    return MAGIC + struct.pack(">I", len(body)) + body


def _looks_like_object_payload(data: bytes) -> bool:
    return bool(
        data
        and (
            data[:1] in {b"\x80", b"\x81"}
            or data.startswith(b"pickle")
            or b"__reduce__" in data
            or (data.startswith(b"(") and b"c__builtin__\n" in data)
        )
    )


def decode_frame(
    data: bytes,
    session_key: bytes,
    seen_nonces: Set[str],
) -> Dict[str, Any]:
    if not data:
        raise IpcProtocolError("Empty frame.")
    if _looks_like_object_payload(data):
        raise IpcProtocolError("Python object input is rejected.")
    if len(data) < 8 or data[:4] != MAGIC:
        raise IpcProtocolError("Frame header is invalid.")
    length = struct.unpack(">I", data[4:8])[0]
    if length > MAX_FRAME or length < 2 or len(data) != length + 8:
        raise IpcProtocolError("Frame length is invalid.")
    payload = decode_json_message(data[8:])
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise IpcProtocolError(f"Frame schema missing: {', '.join(missing)}.")
    extra = sorted(set(payload) - set(REQUIRED_FIELDS) - {"detail"})
    if extra:
        raise IpcProtocolError(f"Frame schema unknown fields: {', '.join(extra)}.")
    if payload["v"] != PROTOCOL_VERSION or payload["op"] not in ALLOWED_OPS:
        raise IpcProtocolError("Frame version or operation is invalid.")
    nonce = str(payload["nonce"])
    if not nonce or nonce in seen_nonces:
        raise IpcProtocolError("Frame nonce replay or empty nonce.")
    expected = sign_message(session_key, payload)
    if not hmac.compare_digest(str(payload["mac"]), expected):
        raise IpcProtocolError("Frame authenticator mismatch.")
    seen_nonces.add(nonce)
    return payload


def mailbox_dir(instance_id: str) -> Path:
    del instance_id
    _require_product_ipc_disabled()


def local_ipc_address(instance_id: Optional[str] = None) -> str:
    del instance_id
    _require_product_ipc_disabled()


def local_ipc_family() -> str:
    return TRANSPORT


def local_ipc_transport() -> str:
    return TRANSPORT


def read_session_key(mailbox: Path) -> bytes:
    del mailbox
    _require_product_ipc_disabled()


class LocalIpcServer:
    """Compatibility name that cannot start a filesystem transport."""

    def __init__(self, instance_id: Optional[str] = None):
        del instance_id
        _require_product_ipc_disabled()


def send_raw(address: str, data: bytes) -> None:
    del address, data
    _require_product_ipc_disabled()


def send_signed(address: str, op: str, nonce: str) -> None:
    del address, op, nonce
    _require_product_ipc_disabled()

