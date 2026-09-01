"""Authenticated filesystem-mailbox JSON IPC. No pickle. No sockets.

Frames are length-bounded typed JSON with a per-session HMAC key stored
in a 0600 mailbox file. Replay and size checks are mandatory. This is
not a network transport and not a production authenticator.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import struct
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Set
from uuid import uuid4


MAGIC = b"CTJ1"
MAX_FRAME = 65_536
PROTOCOL_VERSION = 1
ALLOWED_OPS: FrozenSet[str] = frozenset({"ping", "handoff", "status"})
REQUIRED_FIELDS = ("v", "op", "nonce", "mac")
TRANSPORT = "FILESYSTEM_MAILBOX"


class IpcProtocolError(ValueError):
    """Raised when a frame fails magic, size, schema, MAC, or replay checks."""


def mailbox_dir(instance_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"charttrace-ipc-{instance_id}"


def local_ipc_address(instance_id: Optional[str] = None) -> str:
    return str(mailbox_dir(instance_id or str(uuid4())))


def local_ipc_family() -> str:
    return TRANSPORT


def local_ipc_transport() -> str:
    return TRANSPORT


def _session_key_path(mailbox: Path) -> Path:
    return Path(mailbox) / "session.key"


def _inbox_path(mailbox: Path) -> Path:
    return Path(mailbox) / "inbox.ctj"


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
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_FRAME:
        raise IpcProtocolError("IPC frame exceeds size bound.")
    return MAGIC + struct.pack(">I", len(body)) + body


def _looks_like_object_payload(data: bytes) -> bool:
    if not data:
        return False
    if data[:1] in {b"\x80", b"\x81"}:
        return True
    if data.startswith(b"pickle") or b"__reduce__" in data:
        return True
    if data.startswith(b"(") and b"c__builtin__\n" in data:
        return True
    return False


def decode_frame(data: bytes, session_key: bytes, seen_nonces: Set[str]) -> Dict[str, Any]:
    if not data:
        raise IpcProtocolError("Empty IPC frame.")
    if _looks_like_object_payload(data):
        raise IpcProtocolError("Object/pickle input is rejected.")
    if data[:4] != MAGIC:
        raise IpcProtocolError("IPC magic mismatch.")
    if len(data) < 8:
        raise IpcProtocolError("IPC frame is truncated.")
    length = struct.unpack(">I", data[4:8])[0]
    if length > MAX_FRAME or length < 2:
        raise IpcProtocolError("IPC frame length is invalid.")
    body = data[8 : 8 + length]
    if len(body) != length:
        raise IpcProtocolError("IPC frame is truncated.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IpcProtocolError("IPC body is not typed JSON.") from error
    if not isinstance(payload, dict):
        raise IpcProtocolError("IPC body must be a JSON object.")
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise IpcProtocolError(f"IPC schema missing: {', '.join(missing)}.")
    extra = sorted(set(payload) - set(REQUIRED_FIELDS) - {"detail"})
    if extra:
        raise IpcProtocolError(f"IPC schema unknown fields: {', '.join(extra)}.")
    if payload["v"] != PROTOCOL_VERSION:
        raise IpcProtocolError("IPC protocol version mismatch.")
    if payload["op"] not in ALLOWED_OPS:
        raise IpcProtocolError("IPC operation is not allowed.")
    nonce = str(payload["nonce"])
    if not nonce or nonce in seen_nonces:
        raise IpcProtocolError("IPC nonce replay or empty nonce.")
    expected = sign_message(session_key, payload)
    if not hmac.compare_digest(str(payload["mac"]), expected):
        raise IpcProtocolError("IPC authenticator mismatch.")
    seen_nonces.add(nonce)
    return payload


class LocalIpcServer:
    """Same-host mailbox listener. Never deserializes Python objects."""

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
        mailbox.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(mailbox, 0o700)
        except OSError:
            pass
        key = os.urandom(32)
        key_path = _session_key_path(mailbox)
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
        deadline = time.time() + timeout
        while time.time() < deadline:
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
    mailbox.mkdir(parents=True, exist_ok=True)
    if _looks_like_object_payload(data):
        # Still write so the server observes the malicious frame.
        pass
    temporary = mailbox / "inbox.tmp"
    inbox = _inbox_path(mailbox)
    temporary.write_bytes(data)
    os.replace(temporary, inbox)


def send_signed(address: str, op: str, nonce: str) -> None:
    session_key = read_session_key(Path(address))
    payload = {"v": PROTOCOL_VERSION, "op": op, "nonce": nonce}
    payload["mac"] = sign_message(session_key, payload)
    send_raw(address, encode_frame(payload))
