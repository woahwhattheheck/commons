#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed, process-isolated TITAN agent session runner.

The parent creates one :class:`IsolatedAgentSession` per literal game cell and
forwards each agent callback to a clean ``python -I -B`` worker.  The worker
loads an exact, privately materialized runtime tree, keeps state only for that
session, and proves the transitive import/tree closure before and after calls.

This module is stdlib-only and intentionally does not know Kaggriculture game
semantics.  It supplies an isolation boundary that existing evaluators can use
as a drop-in callable via ``session.as_agent()``.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import importlib
import io
import json
import math
import os
import pathlib
import queue
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final, TextIO

BINDING_SCHEMA: Final = "titan.transitive-runtime-binding.v1"
CELL_SCHEMA: Final = "titan.transitive-arm-cell.v1"
PROTOCOL_SCHEMA: Final = "titan.transitive-arm-protocol.v1"
RECEIPT_SCHEMA: Final = "titan.transitive-arm-session-receipt.v1"
DEFAULT_MAX_FILES: Final = 4096
DEFAULT_MAX_TOTAL_BYTES: Final = 32 * 1024 * 1024
DEFAULT_MAX_FILE_BYTES: Final = 4 * 1024 * 1024
DEFAULT_MAX_MESSAGE_BYTES: Final = 8 * 1024 * 1024
DEFAULT_MAX_LOG_BYTES: Final = 64 * 1024


class IsolationError(RuntimeError):
    """Base class for deterministic fail-closed errors."""


class BindingError(IsolationError):
    """Runtime tree or metadata failed exact binding."""


class ProtocolError(IsolationError):
    """The worker protocol was malformed or internally inconsistent."""


class WorkerFailure(IsolationError):
    """The isolated worker reported a controlled failure."""


class WorkerTimeout(IsolationError):
    """The isolated worker exceeded a declared request deadline."""


def _is_exact_int(value: Any) -> bool:
    return type(value) is int


def _validate_json(value: Any, *, path: str = "$", depth: int = 0) -> None:
    if depth > 100:
        raise ProtocolError(f"JSON nesting exceeds 100 at {path}")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ProtocolError(f"non-finite number at {path}")
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _validate_json(child, path=f"{path}[{index}]", depth=depth + 1)
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ProtocolError(f"non-string object key at {path}")
            _validate_json(child, path=f"{path}.{key}", depth=depth + 1)
        return
    raise ProtocolError(f"non-JSON value {type(value).__name__} at {path}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def strict_loads(text: str) -> Any:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ProtocolError(f"non-finite JSON token: {token}")
            ),
        )
    except IsolationError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc
    _validate_json(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    _validate_json(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ProtocolError(f"cannot canonicalize JSON: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_root(root: os.PathLike[str] | str, *, label: str = "runtime root") -> pathlib.Path:
    raw = pathlib.Path(root)
    try:
        if raw.is_symlink():
            raise BindingError(f"{label} symlink rejected: {raw}")
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise BindingError(f"cannot resolve {label} {raw}: {exc}") from exc
    if not resolved.is_dir():
        raise BindingError(f"{label} is not a directory: {resolved}")
    return resolved


def _safe_relative_path(raw: str, *, label: str) -> pathlib.PurePosixPath:
    if type(raw) is not str or not raw:
        raise BindingError(f"{label} must be a nonempty string")
    if "\\" in raw or "\x00" in raw:
        raise BindingError(f"unsafe {label}: {raw!r}")
    path = pathlib.PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise BindingError(f"unsafe {label}: {raw!r}")
    return path


def _regular_file_inventory(
    root: pathlib.Path,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict[str, dict[str, Any]]:
    root = _resolve_root(root)
    inventory: dict[str, dict[str, Any]] = {}
    total = 0
    for candidate in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
        try:
            info = candidate.lstat()
        except OSError as exc:
            raise BindingError(f"cannot stat {candidate}: {exc}") from exc
        rel = candidate.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode):
            raise BindingError(f"symlink rejected: {rel}")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise BindingError(f"non-regular runtime member rejected: {rel}")
        if info.st_nlink != 1:
            raise BindingError(f"hard-linked runtime member rejected: {rel}")
        if rel.endswith(".pyc") or "__pycache__" in pathlib.PurePosixPath(rel).parts:
            raise BindingError(f"bytecode runtime member rejected: {rel}")
        if info.st_size > max_file_bytes:
            raise BindingError(f"runtime member exceeds byte limit: {rel}")
        total += info.st_size
        if total > max_total_bytes:
            raise BindingError("runtime tree exceeds total byte limit")
        if len(inventory) >= max_files:
            raise BindingError("runtime tree exceeds file-count limit")
        inventory[rel] = {"bytes": info.st_size, "sha256": sha256_file(candidate)}
    if not inventory:
        raise BindingError("runtime tree is empty")
    return inventory


def _tree_sha256(files: Mapping[str, Mapping[str, Any]]) -> str:
    normalized: list[dict[str, Any]] = []
    for path in sorted(files):
        record = files[path]
        normalized.append(
            {
                "path": path,
                "bytes": record.get("bytes"),
                "sha256": record.get("sha256"),
            }
        )
    return sha256_bytes(canonical_bytes(normalized))


def build_binding(
    root: os.PathLike[str] | str,
    *,
    entrypoint: str = "main.py",
    callable_name: str = "agent",
) -> dict[str, Any]:
    root_path = _resolve_root(root)
    entry_rel = _safe_relative_path(entrypoint, label="entrypoint")
    if entry_rel.suffix != ".py":
        raise BindingError("entrypoint must be a .py file")
    if type(callable_name) is not str or not callable_name.isidentifier():
        raise BindingError("callable must be a Python identifier")
    files = _regular_file_inventory(root_path)
    entry_key = entry_rel.as_posix()
    if entry_key not in files:
        raise BindingError(f"entrypoint not present in runtime tree: {entry_key}")
    binding: dict[str, Any] = {
        "schema": BINDING_SCHEMA,
        "entrypoint": entry_key,
        "callable": callable_name,
        "files": files,
        "tree_sha256": _tree_sha256(files),
    }
    binding["binding_sha256"] = sha256_bytes(canonical_bytes(binding))
    return binding


def validate_binding(binding: Any) -> dict[str, Any]:
    if type(binding) is not dict:
        raise BindingError("binding must be an object")
    required = {
        "schema",
        "entrypoint",
        "callable",
        "files",
        "tree_sha256",
        "binding_sha256",
    }
    if set(binding) != required:
        raise BindingError(f"binding keys must equal {sorted(required)!r}")
    if binding["schema"] != BINDING_SCHEMA:
        raise BindingError("unsupported binding schema")
    entry = _safe_relative_path(binding["entrypoint"], label="entrypoint")
    if entry.suffix != ".py":
        raise BindingError("entrypoint must be a .py file")
    callable_name = binding["callable"]
    if type(callable_name) is not str or not callable_name.isidentifier():
        raise BindingError("callable must be a Python identifier")
    files = binding["files"]
    if type(files) is not dict or not files:
        raise BindingError("binding files must be a nonempty object")
    if len(files) > DEFAULT_MAX_FILES:
        raise BindingError("binding exceeds file-count limit")
    clean_files: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for raw_path, raw_record in files.items():
        path = _safe_relative_path(raw_path, label="runtime member").as_posix()
        if path != raw_path:
            raise BindingError(f"noncanonical runtime member: {raw_path!r}")
        if type(raw_record) is not dict or set(raw_record) != {"bytes", "sha256"}:
            raise BindingError(f"invalid runtime record: {path}")
        size = raw_record["bytes"]
        digest = raw_record["sha256"]
        if not _is_exact_int(size) or size < 0 or size > DEFAULT_MAX_FILE_BYTES:
            raise BindingError(f"invalid byte count for {path}")
        if type(digest) is not str or len(digest) != 64:
            raise BindingError(f"invalid SHA-256 for {path}")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise BindingError(f"invalid SHA-256 for {path}") from exc
        if digest.lower() != digest:
            raise BindingError(f"SHA-256 must be lowercase for {path}")
        total_bytes += size
        if total_bytes > DEFAULT_MAX_TOTAL_BYTES:
            raise BindingError("binding exceeds total byte limit")
        clean_files[path] = {"bytes": size, "sha256": digest}
    if entry.as_posix() not in clean_files:
        raise BindingError("entrypoint missing from binding files")
    expected_tree = _tree_sha256(clean_files)
    if binding["tree_sha256"] != expected_tree:
        raise BindingError("tree SHA-256 mismatch")
    unsigned = dict(binding)
    claimed = unsigned.pop("binding_sha256")
    if type(claimed) is not str or claimed != sha256_bytes(canonical_bytes(unsigned)):
        raise BindingError("binding SHA-256 mismatch")
    return {
        "schema": BINDING_SCHEMA,
        "entrypoint": entry.as_posix(),
        "callable": callable_name,
        "files": clean_files,
        "tree_sha256": expected_tree,
        "binding_sha256": claimed,
    }


def verify_runtime(root: os.PathLike[str] | str, binding: Mapping[str, Any]) -> None:
    checked = validate_binding(binding)
    actual = _regular_file_inventory(pathlib.Path(root))
    if actual != checked["files"]:
        expected_paths = set(checked["files"])
        actual_paths = set(actual)
        added = sorted(actual_paths - expected_paths)
        removed = sorted(expected_paths - actual_paths)
        changed = sorted(
            path
            for path in expected_paths & actual_paths
            if actual[path] != checked["files"][path]
        )
        raise BindingError(
            f"runtime tree drift: added={added}, removed={removed}, changed={changed}"
        )
    if _tree_sha256(actual) != checked["tree_sha256"]:
        raise BindingError("runtime tree digest mismatch")


def _copy_runtime(source: pathlib.Path, destination: pathlib.Path, binding: Mapping[str, Any]) -> None:
    verify_runtime(source, binding)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    checked = validate_binding(binding)
    for rel in sorted(checked["files"]):
        src = source / pathlib.PurePosixPath(rel)
        dst = destination / pathlib.PurePosixPath(rel)
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with src.open("rb") as reader, dst.open("xb") as writer:
            shutil.copyfileobj(reader, writer, 1024 * 1024)
        os.chmod(dst, 0o444)
    for directory in sorted(
        (path for path in destination.rglob("*") if path.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        os.chmod(directory, 0o555)
    os.chmod(destination, 0o555)
    verify_runtime(destination, binding)
    verify_runtime(source, binding)


def _validate_sha256(value: Any, *, label: str) -> str:
    if type(value) is not str or len(value) != 64 or value.lower() != value:
        raise ProtocolError(f"{label} must be lowercase 64-hex SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ProtocolError(f"{label} must be lowercase 64-hex SHA-256") from exc
    return value


def validate_cell(cell: Any) -> dict[str, Any]:
    if type(cell) is not dict:
        raise ProtocolError("cell identity must be an object")
    required = {
        "schema",
        "arm",
        "opponent",
        "seed",
        "candidate_seat",
        "engine_sha256",
        "evaluator_sha256",
        "opponent_sha256",
        "schedule_sha256",
        "invocation_id",
    }
    if set(cell) != required:
        raise ProtocolError(f"cell keys must equal {sorted(required)!r}")
    if cell["schema"] != CELL_SCHEMA:
        raise ProtocolError("unsupported cell schema")
    for key in ("arm", "opponent", "invocation_id"):
        value = cell[key]
        if type(value) is not str or not value or len(value) > 200:
            raise ProtocolError(f"cell {key} must be a nonempty bounded string")
    if not _is_exact_int(cell["seed"]) or not 0 <= cell["seed"] < 2**63:
        raise ProtocolError("cell seed must be a nonnegative exact integer")
    if not _is_exact_int(cell["candidate_seat"]) or cell["candidate_seat"] not in (0, 1):
        raise ProtocolError("candidate_seat must be exact integer 0 or 1")
    for key in ("engine_sha256", "evaluator_sha256", "opponent_sha256", "schedule_sha256"):
        _validate_sha256(cell[key], label=f"cell {key}")
    return dict(cell)


def _session_sha256(binding: Mapping[str, Any], cell: Mapping[str, Any]) -> str:
    return sha256_bytes(
        canonical_bytes(
            {"binding_sha256": binding["binding_sha256"], "cell": dict(cell)}
        )
    )


def _module_name_from_entrypoint(entrypoint: str) -> str:
    path = pathlib.PurePosixPath(entrypoint)
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    if not parts or any(not part.isidentifier() for part in parts):
        raise BindingError(f"entrypoint is not importable as a module: {entrypoint}")
    return ".".join(parts)


def _runtime_top_level_names(binding: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    files = binding["files"]
    for rel in files:
        path = pathlib.PurePosixPath(rel)
        if len(path.parts) == 1 and path.suffix == ".py" and path.stem.isidentifier():
            names.add(path.stem)
        elif len(path.parts) >= 2 and path.parts[0].isidentifier():
            if f"{path.parts[0]}/__init__.py" in files:
                names.add(path.parts[0])
    return names


def _is_within(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _dynamic_import_manifest(
    root: pathlib.Path,
    binding: Mapping[str, Any],
    runtime_names: set[str],
) -> list[dict[str, str]]:
    expected_files = binding["files"]
    records: list[dict[str, str]] = []
    violations: list[str] = []
    for name, module in sorted(sys.modules.items()):
        top = name.split(".", 1)[0]
        raw_file = getattr(module, "__file__", None)
        if raw_file is None:
            if top in runtime_names and name != "__main__":
                violations.append(f"runtime module has no source file: {name}")
            continue
        try:
            path = pathlib.Path(raw_file).resolve(strict=True)
        except (OSError, RuntimeError):
            if top in runtime_names:
                violations.append(f"runtime module source is unresolved: {name}={raw_file!r}")
            continue
        if _is_within(path, root):
            rel = path.relative_to(root).as_posix()
            if rel not in expected_files:
                violations.append(f"imported unbound runtime source: {name}={rel}")
                continue
            digest = sha256_file(path)
            if digest != expected_files[rel]["sha256"]:
                violations.append(f"imported runtime source drift: {name}={rel}")
                continue
            records.append({"module": name, "path": rel, "sha256": digest})
        elif top in runtime_names:
            violations.append(f"runtime module escaped root: {name}={path}")
    if violations:
        raise BindingError("; ".join(violations))
    return records


def _strict_env(private_home: pathlib.Path) -> dict[str, str]:
    keep = (
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
    )
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env.update(
        {
            "HOME": str(private_home),
            "USERPROFILE": str(private_home),
            "TMPDIR": str(private_home),
            "TMP": str(private_home),
            "TEMP": str(private_home),
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    return env


def _kill_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover - exercised on Windows runners only
            process.kill()
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        process.kill()


def _readline_with_timeout(stream: TextIO, timeout: float) -> str:
    if timeout <= 0 or not math.isfinite(timeout):
        raise ValueError("timeout must be positive and finite")
    if os.name == "posix":
        selector = selectors.DefaultSelector()
        try:
            selector.register(stream, selectors.EVENT_READ)
            if not selector.select(timeout):
                raise WorkerTimeout("worker response timed out")
            line = stream.readline()
        finally:
            selector.close()
        return line

    result: queue.Queue[object] = queue.Queue(maxsize=1)  # pragma: no cover

    def reader() -> None:  # pragma: no cover
        try:
            result.put(stream.readline())
        except BaseException as exc:
            result.put(exc)

    threading.Thread(target=reader, daemon=True).start()  # pragma: no cover
    try:
        value = result.get(timeout=timeout)
    except queue.Empty as exc:  # pragma: no cover
        raise WorkerTimeout("worker response timed out") from exc
    if isinstance(value, BaseException):  # pragma: no cover
        raise value
    return str(value)


class _BoundedTextSink(io.TextIOBase):
    def __init__(self, limit: int) -> None:
        super().__init__()
        self._limit = limit
        self._prefix = bytearray()
        self._digest = hashlib.sha256()
        self._bytes = 0

    @property
    def encoding(self) -> str:
        return "utf-8"

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        if type(value) is not str:
            value = str(value)
        data = value.encode("utf-8", "replace")
        self._digest.update(data)
        self._bytes += len(data)
        remaining = max(0, self._limit - len(self._prefix))
        if remaining:
            self._prefix.extend(data[:remaining])
        return len(value)

    def flush(self) -> None:
        return None

    def receipt(self) -> dict[str, Any]:
        return {
            "bytes": self._bytes,
            "sha256": self._digest.hexdigest(),
            "truncated": self._bytes > self._limit,
            "text": bytes(self._prefix).decode("utf-8", "replace"),
        }


def _empty_log(limit: int) -> dict[str, Any]:
    return _BoundedTextSink(limit).receipt()


@dataclasses.dataclass(frozen=True)
class CallResult:
    value: Any
    receipt: dict[str, Any]


class IsolatedAgentSession:
    """One fresh transitive runtime for one literal arm/game/seat session."""

    def __init__(
        self,
        source_root: os.PathLike[str] | str,
        binding: Mapping[str, Any],
        cell: Mapping[str, Any],
        *,
        timeout: float = 10.0,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
        max_log_bytes: int = DEFAULT_MAX_LOG_BYTES,
    ) -> None:
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise ProtocolError("timeout must be numeric")
        timeout = float(timeout)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ProtocolError("timeout must be positive and finite")
        if not _is_exact_int(max_message_bytes) or not 1024 <= max_message_bytes <= 64 * 1024 * 1024:
            raise ProtocolError("invalid max_message_bytes")
        if not _is_exact_int(max_log_bytes) or not 0 <= max_log_bytes <= 1024 * 1024:
            raise ProtocolError("invalid max_log_bytes")
        self._source_root = _resolve_root(source_root, label="source runtime root")
        self._binding = validate_binding(dict(binding))
        self._cell = validate_cell(dict(cell))
        self._session_sha256 = _session_sha256(self._binding, self._cell)
        self._timeout = timeout
        self._max_message_bytes = max_message_bytes
        self._max_log_bytes = max_log_bytes
        self._temp: tempfile.TemporaryDirectory[str] | None = None
        self._process: subprocess.Popen[str] | None = None
        self._arena: pathlib.Path | None = None
        self._next_seq = 0
        self._final_receipt: dict[str, Any] | None = None
        self._closed = False
        self._start()

    @property
    def cell(self) -> dict[str, Any]:
        return dict(self._cell)

    @property
    def binding(self) -> dict[str, Any]:
        return json.loads(canonical_bytes(self._binding))

    def _start(self) -> None:
        verify_runtime(self._source_root, self._binding)
        self._temp = tempfile.TemporaryDirectory(prefix="titan-arm-cell-")
        private_root = pathlib.Path(self._temp.name)
        self._arena = private_root / "runtime"
        private_home = private_root / "home"
        private_cwd = private_root / "cwd"
        private_home.mkdir(mode=0o700)
        private_cwd.mkdir(mode=0o700)
        _copy_runtime(self._source_root, self._arena, self._binding)
        command = [sys.executable, "-I", "-B", str(pathlib.Path(__file__).resolve()), "--worker"]
        kwargs: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "strict",
            "cwd": private_cwd,
            "env": _strict_env(private_home),
            "bufsize": 1,
        }
        if os.name == "posix":
            kwargs["start_new_session"] = True
        self._process = subprocess.Popen(command, **kwargs)
        request = {
            "schema": PROTOCOL_SCHEMA,
            "op": "bootstrap",
            "runtime_root": str(self._arena),
            "binding": self._binding,
            "cell": self._cell,
            "limits": {
                "max_message_bytes": self._max_message_bytes,
                "max_log_bytes": self._max_log_bytes,
            },
        }
        try:
            response = self._request(request, timeout=max(self._timeout, 10.0))
        except BaseException:
            self.abort()
            raise
        if response.get("op") != "ready":
            self.abort()
            raise ProtocolError("worker did not return ready")
        if response.get("cell") != self._cell:
            self.abort()
            raise ProtocolError("worker relabeled cell identity")
        if response.get("binding_sha256") != self._binding["binding_sha256"]:
            self.abort()
            raise ProtocolError("worker relabeled runtime binding")
        if response.get("session_sha256") != self._session_sha256:
            self.abort()
            raise ProtocolError("worker relabeled session identity")

    def _request(
        self, payload: dict[str, Any], *, timeout: float | None = None
    ) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise ProtocolError("worker process is unavailable")
        data = canonical_bytes(payload)
        if len(data) > self._max_message_bytes:
            raise ProtocolError("request exceeds message byte limit")
        try:
            process.stdin.write(data.decode("utf-8") + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            stderr = self._drain_stderr()
            raise WorkerFailure(f"worker pipe failed: {exc}; stderr={stderr!r}") from exc
        try:
            line = _readline_with_timeout(
                process.stdout, self._timeout if timeout is None else timeout
            )
        except WorkerTimeout:
            _kill_process(process)
            raise
        if not line:
            stderr = self._drain_stderr()
            code = process.poll()
            raise WorkerFailure(f"worker exited without response (rc={code}): {stderr}")
        encoded = line.encode("utf-8", "strict")
        if len(encoded) > self._max_message_bytes:
            _kill_process(process)
            raise ProtocolError("worker response exceeds message byte limit")
        response = strict_loads(line)
        if type(response) is not dict:
            raise ProtocolError("worker response must be an object")
        if response.get("schema") != PROTOCOL_SCHEMA:
            raise ProtocolError("worker response schema mismatch")
        if response.get("cell") != self._cell:
            raise ProtocolError("worker response cell mismatch")
        if response.get("ok") is not True:
            error = response.get("error")
            if type(error) is not dict:
                raise ProtocolError("worker failure lacks structured error")
            raise WorkerFailure(f"{error.get('type')}: {error.get('message')}")
        return response

    def _drain_stderr(self) -> str:
        process = self._process
        if process is None or process.stderr is None:
            return ""
        if process.poll() is None:
            return ""
        try:
            return process.stderr.read()[-4096:]
        except (OSError, UnicodeError):
            return ""

    def call(self, *args: Any, **kwargs: Any) -> CallResult:
        if self._closed or self._final_receipt is not None:
            raise ProtocolError("session is closed")
        args_list = list(args)
        _validate_json(args_list)
        _validate_json(kwargs)
        seq = self._next_seq
        request = {
            "schema": PROTOCOL_SCHEMA,
            "op": "call",
            "cell": self._cell,
            "seq": seq,
            "args": args_list,
            "kwargs": kwargs,
        }
        try:
            response = self._request(request)
        except BaseException:
            self.abort()
            raise
        if response.get("op") != "result" or response.get("seq") != seq:
            self.abort()
            raise ProtocolError("worker response sequence mismatch")
        if response.get("session_sha256") != self._session_sha256:
            self.abort()
            raise ProtocolError("worker result session mismatch")
        self._next_seq += 1
        return CallResult(response.get("value"), dict(response.get("receipt", {})))

    def as_agent(self) -> Callable[..., Any]:
        def isolated_agent(*args: Any, **kwargs: Any) -> Any:
            return self.call(*args, **kwargs).value

        return isolated_agent

    def finalize(self) -> dict[str, Any]:
        if self._final_receipt is not None:
            return json.loads(canonical_bytes(self._final_receipt))
        if self._closed:
            raise ProtocolError("session is closed")
        response = self._request(
            {
                "schema": PROTOCOL_SCHEMA,
                "op": "finalize",
                "cell": self._cell,
                "call_count": self._next_seq,
            },
            timeout=max(self._timeout, 10.0),
        )
        if response.get("op") != "finalized":
            self.abort()
            raise ProtocolError("worker did not finalize")
        if response.get("session_sha256") != self._session_sha256:
            self.abort()
            raise ProtocolError("worker final response session mismatch")
        receipt = response.get("receipt")
        if type(receipt) is not dict:
            self.abort()
            raise ProtocolError("worker final receipt missing")
        if receipt.get("schema") != RECEIPT_SCHEMA:
            self.abort()
            raise ProtocolError("worker final receipt schema mismatch")
        if receipt.get("cell") != self._cell:
            self.abort()
            raise ProtocolError("worker final receipt cell mismatch")
        if receipt.get("binding_sha256") != self._binding["binding_sha256"]:
            self.abort()
            raise ProtocolError("worker final receipt binding mismatch")
        if receipt.get("session_sha256") != self._session_sha256:
            self.abort()
            raise ProtocolError("worker final receipt session mismatch")
        if receipt.get("call_count") != self._next_seq:
            self.abort()
            raise ProtocolError("worker final receipt call-count mismatch")
        unsigned = dict(receipt)
        claimed_seal = unsigned.pop("receipt_sha256", None)
        if claimed_seal != sha256_bytes(canonical_bytes(unsigned)):
            self.abort()
            raise ProtocolError("worker final receipt seal mismatch")
        try:
            assert self._arena is not None
            verify_runtime(self._arena, self._binding)
            self._final_receipt = dict(receipt)
            process = self._process
            if process is not None:
                if process.stdin is not None:
                    process.stdin.close()
                try:
                    code = process.wait(timeout=self._timeout)
                except subprocess.TimeoutExpired as exc:
                    _kill_process(process)
                    raise WorkerTimeout("worker did not exit after finalize") from exc
                if code != 0:
                    raise WorkerFailure(f"worker exited nonzero after finalize: {code}")
            result = json.loads(canonical_bytes(self._final_receipt))
            self._closed = True
            self._cleanup()
            return result
        except BaseException:
            self.abort()
            raise

    def abort(self) -> None:
        if self._closed:
            return
        if self._process is not None:
            _kill_process(self._process)
        self._closed = True
        self._cleanup()

    def _cleanup(self) -> None:
        process = self._process
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    try:
                        stream.close()
                    except OSError:
                        pass
            self._process = None
        if self._temp is not None:
            try:
                self._temp.cleanup()
            finally:
                self._temp = None

    def __enter__(self) -> "IsolatedAgentSession":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is None:
            self.finalize()
        else:
            self.abort()


def _worker_send(protocol_out: TextIO, payload: dict[str, Any], max_bytes: int) -> None:
    data = canonical_bytes(payload)
    if len(data) > max_bytes:
        fallback = {
            "schema": PROTOCOL_SCHEMA,
            "ok": False,
            "cell": payload.get("cell"),
            "error": {
                "type": "ProtocolError",
                "message": "response exceeds message byte limit",
            },
        }
        data = canonical_bytes(fallback)
    protocol_out.write(data.decode("utf-8") + "\n")
    protocol_out.flush()


def _worker_error(cell: Any, exc: BaseException) -> dict[str, Any]:
    return {
        "schema": PROTOCOL_SCHEMA,
        "ok": False,
        "cell": cell,
        "error": {"type": type(exc).__name__, "message": str(exc)[:4000]},
    }


def _worker_main() -> int:
    protocol_in = sys.stdin
    protocol_out = sys.stdout
    max_message_bytes = DEFAULT_MAX_MESSAGE_BYTES
    max_log_bytes = DEFAULT_MAX_LOG_BYTES
    cell: dict[str, Any] | None = None
    root: pathlib.Path | None = None
    binding: dict[str, Any] | None = None
    session_sha256: str | None = None
    runtime_names: set[str] = set()
    agent: Callable[..., Any] | None = None
    calls: list[dict[str, Any]] = []
    import_log = {"stdout": _empty_log(max_log_bytes), "stderr": _empty_log(max_log_bytes)}

    first = protocol_in.readline()
    if not first:
        return 2
    try:
        bootstrap = strict_loads(first)
        if type(bootstrap) is not dict or bootstrap.get("schema") != PROTOCOL_SCHEMA:
            raise ProtocolError("invalid bootstrap envelope")
        if bootstrap.get("op") != "bootstrap":
            raise ProtocolError("first operation must be bootstrap")
        cell = validate_cell(bootstrap.get("cell"))
        binding = validate_binding(bootstrap.get("binding"))
        session_sha256 = _session_sha256(binding, cell)
        limits = bootstrap.get("limits")
        if type(limits) is not dict or set(limits) != {"max_message_bytes", "max_log_bytes"}:
            raise ProtocolError("invalid worker limits")
        max_message_bytes = limits["max_message_bytes"]
        max_log_bytes = limits["max_log_bytes"]
        if not _is_exact_int(max_message_bytes) or not 1024 <= max_message_bytes <= 64 * 1024 * 1024:
            raise ProtocolError("invalid max_message_bytes")
        if not _is_exact_int(max_log_bytes) or not 0 <= max_log_bytes <= 1024 * 1024:
            raise ProtocolError("invalid max_log_bytes")
        raw_root = bootstrap.get("runtime_root")
        if type(raw_root) is not str:
            raise ProtocolError("runtime_root must be a string")
        root = _resolve_root(raw_root, label="private runtime root")
        verify_runtime(root, binding)
        runtime_names = _runtime_top_level_names(binding)
        collisions = sorted(name for name in runtime_names if name in sys.modules and name != "__main__")
        if collisions:
            raise BindingError(f"runtime module names already loaded: {collisions}")

        # Remove controller/cwd paths.  The clean worker may import only the
        # exact runtime root plus interpreter-provided stdlib/site roots.
        controller_dir = pathlib.Path(__file__).resolve().parent
        cwd = pathlib.Path.cwd().resolve()
        retained: list[str] = []
        for raw in sys.path:
            if not raw:
                continue
            try:
                resolved = pathlib.Path(raw).resolve()
            except OSError:
                continue
            if resolved in (controller_dir, cwd):
                continue
            retained.append(str(resolved))
        sys.path[:] = [str(root), *retained]

        module_name = _module_name_from_entrypoint(binding["entrypoint"])
        stdout_buffer = _BoundedTextSink(max_log_bytes)
        stderr_buffer = _BoundedTextSink(max_log_bytes)
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            module = importlib.import_module(module_name)
        import_log = {"stdout": stdout_buffer.receipt(), "stderr": stderr_buffer.receipt()}
        candidate = getattr(module, binding["callable"], None)
        if not callable(candidate):
            raise BindingError(
                f"entrypoint {binding['entrypoint']} lacks callable {binding['callable']}"
            )
        agent = candidate
        imported = _dynamic_import_manifest(root, binding, runtime_names)
        verify_runtime(root, binding)
        _worker_send(
            protocol_out,
            {
                "schema": PROTOCOL_SCHEMA,
                "ok": True,
                "op": "ready",
                "cell": cell,
                "binding_sha256": binding["binding_sha256"],
                "session_sha256": session_sha256,
                "tree_sha256": binding["tree_sha256"],
                "imported_modules": imported,
                "import_log": import_log,
            },
            max_message_bytes,
        )
    except BaseException as exc:
        _worker_send(protocol_out, _worker_error(cell, exc), max_message_bytes)
        return 2

    assert cell is not None and root is not None and binding is not None and agent is not None
    for line in protocol_in:
        try:
            if len(line.encode("utf-8", "strict")) > max_message_bytes:
                raise ProtocolError("request exceeds message byte limit")
            request = strict_loads(line)
            if type(request) is not dict or request.get("schema") != PROTOCOL_SCHEMA:
                raise ProtocolError("invalid request envelope")
            if request.get("cell") != cell:
                raise ProtocolError("request cell identity mismatch")
            op = request.get("op")
            if op == "call":
                seq = request.get("seq")
                if not _is_exact_int(seq) or seq != len(calls):
                    raise ProtocolError("call sequence mismatch")
                args = request.get("args")
                kwargs = request.get("kwargs")
                if type(args) is not list or type(kwargs) is not dict:
                    raise ProtocolError("call args/kwargs malformed")
                _validate_json(args)
                _validate_json(kwargs)
                before_tree = _tree_sha256(_regular_file_inventory(root))
                if before_tree != binding["tree_sha256"]:
                    raise BindingError("runtime tree changed before call")
                stdout_buffer = _BoundedTextSink(max_log_bytes)
                stderr_buffer = _BoundedTextSink(max_log_bytes)
                with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                    value = agent(*args, **kwargs)
                _validate_json(value)
                imported = _dynamic_import_manifest(root, binding, runtime_names)
                verify_runtime(root, binding)
                receipt = {
                    "seq": seq,
                    "session_sha256": session_sha256,
                    "input_sha256": sha256_bytes(canonical_bytes({"args": args, "kwargs": kwargs})),
                    "output_sha256": sha256_bytes(canonical_bytes(value)),
                    "stdout": stdout_buffer.receipt(),
                    "stderr": stderr_buffer.receipt(),
                    "imported_modules_sha256": sha256_bytes(canonical_bytes(imported)),
                }
                calls.append(receipt)
                _worker_send(
                    protocol_out,
                    {
                        "schema": PROTOCOL_SCHEMA,
                        "ok": True,
                        "op": "result",
                        "cell": cell,
                        "session_sha256": session_sha256,
                        "seq": seq,
                        "value": value,
                        "receipt": receipt,
                    },
                    max_message_bytes,
                )
            elif op == "finalize":
                if request.get("call_count") != len(calls):
                    raise ProtocolError("finalize call-count mismatch")
                imported = _dynamic_import_manifest(root, binding, runtime_names)
                verify_runtime(root, binding)
                receipt: dict[str, Any] = {
                    "schema": RECEIPT_SCHEMA,
                    "cell": cell,
                    "binding_sha256": binding["binding_sha256"],
                    "session_sha256": session_sha256,
                    "tree_sha256": binding["tree_sha256"],
                    "entrypoint": binding["entrypoint"],
                    "callable": binding["callable"],
                    "call_count": len(calls),
                    "calls_sha256": sha256_bytes(canonical_bytes(calls)),
                    "imported_modules": imported,
                    "import_log": import_log,
                    "python": {
                        "implementation": sys.implementation.name,
                        "version": [sys.version_info.major, sys.version_info.minor, sys.version_info.micro],
                        "isolated": int(sys.flags.isolated),
                        "no_user_site": int(sys.flags.no_user_site),
                        "dont_write_bytecode": int(sys.flags.dont_write_bytecode),
                    },
                }
                receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
                _worker_send(
                    protocol_out,
                    {
                        "schema": PROTOCOL_SCHEMA,
                        "ok": True,
                        "op": "finalized",
                        "cell": cell,
                        "session_sha256": session_sha256,
                        "receipt": receipt,
                    },
                    max_message_bytes,
                )
                return 0
            else:
                raise ProtocolError(f"unsupported operation: {op!r}")
        except BaseException as exc:
            _worker_send(protocol_out, _worker_error(cell, exc), max_message_bytes)
            return 2
    return 2


def _load_json_file(path: pathlib.Path) -> Any:
    try:
        return strict_loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise IsolationError(f"cannot read {path}: {exc}") from exc


def _write_json_file(path: pathlib.Path, value: Any) -> None:
    data = canonical_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temp = pathlib.Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _cli_bind(args: argparse.Namespace) -> int:
    binding = build_binding(args.root, entrypoint=args.entrypoint, callable_name=args.callable)
    if args.output:
        _write_json_file(pathlib.Path(args.output), binding)
    else:
        sys.stdout.buffer.write(canonical_bytes(binding) + b"\n")
    return 0


def _cli_probe(args: argparse.Namespace) -> int:
    binding = _load_json_file(pathlib.Path(args.binding))
    cell = _load_json_file(pathlib.Path(args.cell))
    calls = _load_json_file(pathlib.Path(args.calls))
    if type(calls) is not list:
        raise ProtocolError("calls file must contain a list")
    results: list[dict[str, Any]] = []
    with IsolatedAgentSession(args.root, binding, cell, timeout=args.timeout) as session:
        for index, record in enumerate(calls):
            if type(record) is not dict or set(record) != {"args", "kwargs"}:
                raise ProtocolError(f"calls[{index}] must contain args and kwargs")
            if type(record["args"]) is not list or type(record["kwargs"]) is not dict:
                raise ProtocolError(f"calls[{index}] args/kwargs malformed")
            result = session.call(*record["args"], **record["kwargs"])
            results.append({"value": result.value, "receipt": result.receipt})
        receipt = session.finalize()
    report = {"results": results, "receipt": receipt}
    if args.output:
        _write_json_file(pathlib.Path(args.output), report)
    else:
        sys.stdout.buffer.write(canonical_bytes(report) + b"\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command")
    bind = subparsers.add_parser("bind", help="emit an exact runtime binding")
    bind.add_argument("root")
    bind.add_argument("--entrypoint", default="main.py")
    bind.add_argument("--callable", default="agent")
    bind.add_argument("--output")
    bind.set_defaults(func=_cli_bind)
    probe = subparsers.add_parser("probe", help="run a JSON call sequence in one isolated session")
    probe.add_argument("root")
    probe.add_argument("--binding", required=True)
    probe.add_argument("--cell", required=True)
    probe.add_argument("--calls", required=True)
    probe.add_argument("--timeout", type=float, default=10.0)
    probe.add_argument("--output")
    probe.set_defaults(func=_cli_probe)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.worker:
        return _worker_main()
    if not hasattr(args, "func"):
        parser.error("a subcommand is required")
    try:
        return int(args.func(args))
    except IsolationError as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
