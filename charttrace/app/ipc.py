"""Authenticated filesystem-mailbox JSON IPC.

Frames are length-bounded typed JSON with a per-session HMAC key in a
same-device 0600 mailbox file. No Python object deserialization, network
transport, or public endpoint is present.
"""

import hashlib
import hmac
import json
import os
import struct
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
from uuid import uuid4

MAGIC = b"CTJ1"
MAX_FRAME = 65_536
MAX_JSON_MESSAGE_BYTES = MAX_FRAME
PROTOCOL_VERSION = 1
ALLOWED_OPS: FrozenSet[str] = frozenset({"ping", "handoff", "status"})
REQUIRED_FIELDS = ("v", "op", "nonce", "mac")
TRANSPORT = "FILESYSTEM_MAILBOX"

class IpcProtocolError(ValueError):
    pass

JsonIpcError = IpcProtocolError

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
        raise IpcProtocolError("JSON IPC message size is invalid.")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise IpcProtocolError("IPC message must be valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise IpcProtocolError("IPC message must be a JSON object.")
    return value

def encode_json_message(value: Dict[str, Any]) -> bytes:
    if not isinstance(value, dict):
        raise IpcProtocolError("IPC response must be a JSON object.")
    try:
        payload = json.dumps(
            value, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise IpcProtocolError("IPC response is not JSON serializable.") from error
    if len(payload) > MAX_JSON_MESSAGE_BYTES:
        raise IpcProtocolError("JSON IPC response is too large.")
    return payload

def mailbox_dir(instance_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"charttrace-ipc-{instance_id}"

def local_ipc_address(instance_id: Optional[str] = None) -> str:
    return str(mailbox_dir(instance_id or str(uuid4())))

def local_ipc_family() -> str:
    return TRANSPORT

def local_ipc_transport() -> str:
    return TRANSPORT

def _session_key_path(mailbox: Path) -> Path:
    return mailbox / "session.key"

def _inbox_path(mailbox: Path) -> Path:
    return mailbox / "inbox.ctj"

def read_session_key(mailbox: Path) -> bytes:
    key_path = _session_key_path(mailbox)
    if not key_path.is_file() or key_path.is_symlink():
        raise IpcProtocolError("IPC session key is missing.")
    key = key_path.read_bytes()
    if len(key) != 32:
        raise IpcProtocolError("IPC session key is corrupt.")
    return key

def sign_message(session_key: bytes, payload: Dict[str, Any]) -> str:
    body = json.dumps(
        {key: payload[key] for key in ("v", "op", "nonce") if key in payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(session_key, body, hashlib.sha256).hexdigest()

def encode_frame(payload: Dict[str, Any]) -> bytes:
    body = encode_json_message(payload)
    if len(body) > MAX_FRAME:
        raise IpcProtocolError("IPC frame exceeds size bound.")
    return MAGIC + struct.pack(">I", len(body)) + body

def _looks_like_object_payload(data: bytes) -> bool:
    return bool(
        data and (
            data[:1] in {b"\x80", b"\x81"}
            or data.startswith(b"pickle")
            or b"__reduce__" in data
            or (data.startswith(b"(") and b"c__builtin__\n" in data)
        )
    )

def decode_frame(data: bytes, session_key: bytes, seen_nonces: Set[str]) -> Dict[str, Any]:
    if not data:
        raise IpcProtocolError("Empty IPC frame.")
    if _looks_like_object_payload(data):
        raise IpcProtocolError("Python object input is rejected.")
    if len(data) < 8 or data[:4] != MAGIC:
        raise IpcProtocolError("IPC frame header is invalid.")
    length = struct.unpack(">I", data[4:8])[0]
    if length > MAX_FRAME or length < 2 or len(data) != length + 8:
        raise IpcProtocolError("IPC frame length is invalid.")
    payload = decode_json_message(data[8:])
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise IpcProtocolError(f"IPC schema missing: {', '.join(missing)}.")
    extra = sorted(set(payload) - set(REQUIRED_FIELDS) - {"detail"})
    if extra:
        raise IpcProtocolError(f"IPC schema unknown fields: {', '.join(extra)}.")
    if payload["v"] != PROTOCOL_VERSION or payload["op"] not in ALLOWED_OPS:
        raise IpcProtocolError("IPC version or operation is invalid.")
    nonce = str(payload["nonce"])
    if not nonce or nonce in seen_nonces:
        raise IpcProtocolError("IPC nonce replay or empty nonce.")
    expected = sign_message(session_key, payload)
    if not hmac.compare_digest(str(payload["mac"]), expected):
        raise IpcProtocolError("IPC authenticator mismatch.")
    seen_nonces.add(nonce)
    return payload

class LocalIpcServer:
    """Same-host mailbox reader for authenticated JSON handoff."""

    def __init__(self, instance_id: Optional[str] = None):
        self.instance_id = instance_id or str(uuid4())
        self.address = local_ipc_address(self.instance_id)
        self.family = TRANSPORT
        self.transport = TRANSPORT
        self._mailbox: Optional[Path] = None
        self._session_key: Optional[bytes] = None
        self._seen_nonces: Set[str] = set()

    @property
    def is_running(self) -> bool:
        return self._mailbox is not None and self._session_key is not None

    def start(self) -> None:
        if self._mailbox is not None:
            return
        mailbox = Path(self.address)
        if mailbox.is_symlink():
            raise IpcProtocolError("IPC mailbox may not be a symbolic link.")
        mailbox.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(mailbox, 0o700)
        except OSError:
            pass
        key = os.urandom(32)
        key_path = _session_key_path(mailbox)
        if key_path.is_symlink():
            raise IpcProtocolError("IPC key may not be a symbolic link.")
        key_path.write_bytes(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        inbox = _inbox_path(mailbox)
        if inbox.exists():
            inbox.unlink()
        self._mailbox = mailbox
        self._session_key = key

    def receive_once(self, timeout: float = 5.0) -> Dict[str, Any]:
        if self._mailbox is None or self._session_key is None:
            raise RuntimeError("Local IPC server is not running.")
        inbox = _inbox_path(self._mailbox)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if inbox.is_symlink():
                raise IpcProtocolError("IPC inbox may not be a symbolic link.")
            if inbox.exists() and inbox.stat().st_size > 0:
                data = inbox.read_bytes()
                try:
                    inbox.unlink()
                except OSError:
                    pass
                return decode_frame(data, self._session_key, self._seen_nonces)
            time.sleep(0.01)
        raise IpcProtocolError("IPC receive timeout.")

    def close(self) -> None:
        mailbox = self._mailbox
        self._mailbox = None
        self._session_key = None
        if mailbox is None or not mailbox.exists():
            return
        for child in mailbox.iterdir():
            try:
                child.unlink()
            except OSError:
                pass
        try:
            mailbox.rmdir()
        except OSError:
            pass

    def __enter__(self) -> "LocalIpcServer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

def send_raw(address: str, data: bytes) -> None:
    mailbox = Path(address)
    if mailbox.is_symlink():
        raise IpcProtocolError("IPC mailbox may not be a symbolic link.")
    mailbox.mkdir(parents=True, exist_ok=True)
    temporary = mailbox / f"inbox-{uuid4().hex}.tmp"
    inbox = _inbox_path(mailbox)
    temporary.write_bytes(data)
    os.replace(temporary, inbox)

def send_signed(address: str, op: str, nonce: str) -> None:
    session_key = read_session_key(Path(address))
    payload: Dict[str, Any] = {"v": PROTOCOL_VERSION, "op": op, "nonce": nonce}
    payload["mac"] = sign_message(session_key, payload)
    send_raw(address, encode_frame(payload))
