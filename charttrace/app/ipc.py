"""Process-local IPC transport.

Windows uses a named pipe and Unix test hosts use a filesystem-domain socket.
There is no internet-family code path and no TCP listener.
"""

import os
import tempfile
from multiprocessing.connection import Listener
from pathlib import Path
from typing import Optional
from uuid import uuid4


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

    def receive_once(self) -> object:
        if self._listener is None:
            raise RuntimeError("Local IPC server is not running.")
        connection = self._listener.accept()
        try:
            return connection.recv()
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
