"""Authenticated local JSON IPC. No pickle. No internet-family sockets.

Windows uses a named-pipe address label plus a local mailbox directory.
Unix test hosts use a filesystem-domain socket. Frames are length-bounded
typed JSON with nonce replay checks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import struct
import tempfile
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Set
from uuid import uuid4


MAGIC = b"CTJ1"
MAX_FRAME = 65_536
PROTOCOL_VERSION = 1
ALLOWED_OPS: FrozenSet[str] = frozenset({"ping", "handoff", "status"})
REQUIRED_FIELDS = ("v", "op", "nonce", "mac")


class IpcProtocolError(ValueError):
    """Raised when a frame fails magic, size, schema, MAC, or replay checks."""


def local_ipc_address(instance_id: Optional[str] = None) -> str:
    token = instance_id or str(uuid4())
    if os.name == "nt":
        return rf"\\.\pipe\charttrace-{token}"
    return str(Path(tempfile.gettempdir()) / f"charttrace-{token}.sock")


def local_ipc_family() -> str:
    return "AF_PIPE" if os.name == "nt" else "AF_UNIX"


def mailbox_dir(instance_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"charttrace-ipc-{instance_id}"


def _mac_key(instance_id: str) -> bytes:
    return hashlib.sha256(f"charttrace-ipc|{instance_id}".encode("utf-8")).digest()


def sign_message(instance_id: str, payload: Dict[str, Any]) -> str:
    body = json.dumps(
        {key: payload[key] for key in ("v", "op", "nonce") if key in payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(_mac_key(instance_id), body, hashlib.sha256).hexdigest()


def encode_frame(payload: Dict[str, Any]) -> bytes:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_FRAME:
        raise IpcProtocolError("IPC frame exceeds size bound.")
    return MAGIC + struct.pack(">I", len(body)) + body


def decode_frame(data: bytes, instance_id: str, seen_nonces: Set[str]) -> Dict[str, Any]:
    if not data:
        raise IpcProtocolError("Empty IPC frame.")
    if data[:1] == b"\x80" or data.startswith(b"pickle") or b"__reduce__" in data:
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
    expected = sign_message(instance_id, payload)
    if not hmac.compare_digest(str(payload["mac"]), expected):
        raise IpcProtocolError("IPC authenticator mismatch.")
    seen_nonces.add(nonce)
    return payload


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        piece = connection.recv(size - len(chunks))
        if not piece:
            raise IpcProtocolError("IPC connection closed.")
        chunks.extend(piece)
        if len(chunks) > MAX_FRAME + 8:
            raise IpcProtocolError("IPC frame exceeds size bound.")
    return bytes(chunks)


class LocalIpcServer:
    """Same-host JSON listener. Never deserializes Python objects."""

    def __init__(self, instance_id: Optional[str] = None):
        self.instance_id = instance_id or str(uuid4())
        self.address = local_ipc_address(self.instance_id)
        self.family = local_ipc_family()
        self._sock: Optional[socket.socket] = None
        self._seen_nonces: Set[str] = set()

    @property
    def is_running(self) -> bool:
        return self._sock is not None

    def start(self) -> None:
        if self._sock is not None:
            return
        if self.family != "AF_UNIX":
            mailbox_dir(self.instance_id).mkdir(parents=True, exist_ok=True)
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.settimeout(5)
            mailbox = str(mailbox_dir(self.instance_id) / "handoff.sock")
            if Path(mailbox).exists():
                Path(mailbox).unlink()
            self._sock.bind(mailbox)
            self._sock.listen(1)
            return
        socket_path = Path(self.address)
        if socket_path.exists():
            socket_path.unlink()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(5)
        self._sock.bind(self.address)
        self._sock.listen(1)

    def receive_once(self) -> Dict[str, Any]:
        if self._sock is None:
            raise RuntimeError("Local IPC server is not running.")
        connection, _ignored = self._sock.accept()
        try:
            header = _recv_exact(connection, 8)
            if header[:1] == b"\x80":
                raise IpcProtocolError("Object/pickle input is rejected.")
            if header[:4] != MAGIC:
                raise IpcProtocolError("IPC magic mismatch.")
            length = struct.unpack(">I", header[4:8])[0]
            if length > MAX_FRAME:
                raise IpcProtocolError("IPC frame exceeds size bound.")
            body = _recv_exact(connection, length)
            return decode_frame(header + body, self.instance_id, self._seen_nonces)
        finally:
            connection.close()

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self.family == "AF_UNIX":
            socket_path = Path(self.address)
            if socket_path.exists():
                socket_path.unlink()
        else:
            mailbox = mailbox_dir(self.instance_id)
            sock = mailbox / "handoff.sock"
            if sock.exists():
                sock.unlink()

    def __enter__(self) -> "LocalIpcServer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def send_raw(address: str, data: bytes) -> None:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.connect(address)
        connection.sendall(data)
    finally:
        connection.close()


def send_signed(instance_id: str, address: str, op: str, nonce: str) -> None:
    payload = {"v": PROTOCOL_VERSION, "op": op, "nonce": nonce}
    payload["mac"] = sign_message(instance_id, payload)
    send_raw(address, encode_frame(payload))
