"""Process-local IPC transport.

Windows uses a named pipe and Unix test hosts use a filesystem-domain socket.
Messages are bounded UTF-8 JSON bytes. There is no object deserialization,
internet-family code path, or TCP listener.
"""

import json
import os
import tempfile
from multiprocessing.connection import Listener
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


MAX_JSON_MESSAGE_BYTES = 1024 * 1024


class JsonIpcError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise JsonIpcError(f"Non-finite JSON constant {value!r} is prohibited.")


def _unique_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonIpcError(f"Duplicate JSON key {key!r} is prohibited.")
        result[key] = value
    return result


def decode_json_message(payload: bytes) -> Dict[str, Any]:
    if not payload or len(payload) > MAX_JSON_MESSAGE_BYTES:
        raise JsonIpcError("JSON IPC message size is invalid.")
    try:
        decoded = payload.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise JsonIpcError("IPC message must be valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise JsonIpcError("IPC message must be a JSON object.")
    return value


def encode_json_message(value: Dict[str, Any]) -> bytes:
    if not isinstance(value, dict):
        raise JsonIpcError("IPC response must be a JSON object.")
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise JsonIpcError("IPC response is not JSON serializable.") from error
    if len(payload) > MAX_JSON_MESSAGE_BYTES:
        raise JsonIpcError("JSON IPC response is too large.")
    return payload


def local_ipc_address(instance_id: Optional[str] = None) -> str:
    token = instance_id or str(uuid4())
    if os.name == "nt":
        return rf"\\.\pipe\charttrace-{token}"
    return str(Path(tempfile.gettempdir()) / f"charttrace-{token}.sock")


def local_ipc_family() -> str:
    return "AF_PIPE" if os.name == "nt" else "AF_UNIX"


class LocalIpcServer:
    """Small request listener for same-host launcher handoff."""

    def __init__(self, instance_id: Optional[str] = None):
        self.address = local_ipc_address(instance_id)
        self.family = local_ipc_family()
        self._listener: Optional[Listener] = None

    @property
    def is_running(self) -> bool:
        return self._listener is not None

    def start(self) -> None:
        if self._listener is not None:
            return
        if self.family == "AF_UNIX":
            socket_path = Path(self.address)
            if socket_path.exists():
                socket_path.unlink()
        self._listener = Listener(address=self.address, family=self.family)

    def receive_once(self) -> Dict[str, Any]:
        if self._listener is None:
            raise RuntimeError("Local IPC server is not running.")
        connection = self._listener.accept()
        try:
            try:
                payload = connection.recv_bytes(MAX_JSON_MESSAGE_BYTES)
            except OSError as error:
                raise JsonIpcError("JSON IPC message exceeded the size limit.") from error
            return decode_json_message(payload)
        finally:
            connection.close()

    def close(self) -> None:
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        if self.family == "AF_UNIX":
            socket_path = Path(self.address)
            if socket_path.exists():
                socket_path.unlink()

    def __enter__(self) -> "LocalIpcServer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
