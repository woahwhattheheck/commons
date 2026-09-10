#!/usr/bin/env python3
"""Sterile launcher and verifier for the pinned Kaggriculture interpreter.

The worker is deliberately a separate ``python -I -B`` process.  The launcher
binds exact engine and worker bytes, rejects ambiguous JSON/protocol output, and
returns a deterministic envelope around the worker's stage-by-stage receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterable

SCHEMA = "titan.v3.official-transition-oracle.envelope.v1"
WORKER_SCHEMA = "titan.v3.official-transition-oracle.worker.v1"
EXPECTED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
EXPECTED_ENGINE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)
MAX_INPUT_BYTES = 1_000_000
MAX_OUTPUT_BYTES = 16_000_000
DEFAULT_TIMEOUT_SECONDS = 20.0

Json = Any


class OracleError(RuntimeError):
    """Raised when source custody, process isolation, or receipt truth fails."""


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _unique_object(pairs: Iterable[tuple[str, Json]]) -> dict[str, Json]:
    out: dict[str, Json] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_loads(text: str) -> Json:
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _assert_finite(value: Json, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path}: non-finite number")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: non-string object key")
            _assert_finite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_finite(child, f"{path}[{index}]")


def canonical_bytes(value: Json) -> bytes:
    _assert_finite(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def semantic_hash(value: Json) -> str:
    return sha256_bytes(canonical_bytes(value))


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _bound_regular_file(path: Path, *, label: str) -> tuple[Path, bytes]:
    try:
        raw_lstat = path.lstat()
    except FileNotFoundError as exc:
        raise OracleError(f"{label} does not exist: {path}") from exc
    if stat.S_ISLNK(raw_lstat.st_mode):
        raise OracleError(f"{label} must not be a symlink: {path}")
    resolved = path.resolve(strict=True)
    st = resolved.stat()
    if not stat.S_ISREG(st.st_mode):
        raise OracleError(f"{label} must be a regular file: {resolved}")
    if st.st_nlink != 1:
        raise OracleError(f"{label} must have link count 1, observed {st.st_nlink}")
    return resolved, resolved.read_bytes()


def _validate_fixture_shape(fixture: Json) -> None:
    if not isinstance(fixture, dict):
        raise OracleError("fixture must be a JSON object")
    allowed = {
        "schema",
        "name",
        "seed",
        "configuration",
        "start_step",
        "overrides",
        "steps",
        "retain_states",
    }
    unknown = sorted(set(fixture) - allowed)
    if unknown:
        raise OracleError(f"fixture has unknown top-level keys: {unknown}")
    if fixture.get("schema") != "titan.v3.official-transition-fixture.v1":
        raise OracleError("fixture schema mismatch")
    name = fixture.get("name")
    if not isinstance(name, str) or not name or len(name) > 160:
        raise OracleError("fixture name must be a nonempty string <=160 chars")
    steps = fixture.get("steps")
    if not isinstance(steps, list) or not (1 <= len(steps) <= 64):
        raise OracleError("fixture steps must contain 1..64 entries")
    start = fixture.get("start_step", 0)
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise OracleError("start_step must be a nonnegative integer")
    for index, row in enumerate(steps):
        if not isinstance(row, dict) or set(row) - {"step", "actions"}:
            raise OracleError(f"steps[{index}] must contain only step/actions")
        expected = start + index
        step = row.get("step", expected)
        if isinstance(step, bool) or not isinstance(step, int) or step != expected:
            raise OracleError(
                f"steps[{index}].step must be contiguous value {expected}"
            )
        actions = row.get("actions")
        if not isinstance(actions, list) or len(actions) != 2:
            raise OracleError(f"steps[{index}].actions must contain two actions")
    overrides = fixture.get("overrides", {})
    if not isinstance(overrides, dict):
        raise OracleError("overrides must be an object")
    if set(overrides) - {"farms", "privates", "market", "town"}:
        raise OracleError("overrides contains an unsupported state surface")
    for key in ("farms", "privates"):
        if key in overrides:
            rows = overrides[key]
            if not isinstance(rows, list) or len(rows) != 2:
                raise OracleError(f"overrides.{key} must contain two patches")
            if any(not isinstance(row, dict) for row in rows):
                raise OracleError(f"overrides.{key} patches must be objects")
    for key in ("market", "town"):
        if key in overrides and not isinstance(overrides[key], dict):
            raise OracleError(f"overrides.{key} must be an object")
    configuration = fixture.get("configuration", {})
    if not isinstance(configuration, dict):
        raise OracleError("configuration must be an object")
    _assert_finite(fixture)


def _invoke_worker(
    *,
    python_executable: Path,
    worker: Path,
    engine: Path,
    engine_blob: str,
    worker_sha256: str,
    fixture_bytes: bytes,
    timeout_seconds: float,
) -> tuple[Json, str, str, int]:
    command = [
        str(python_executable),
        "-I",
        "-B",
        str(worker),
        "--engine",
        str(engine),
        "--expected-engine-blob",
        engine_blob,
        "--expected-worker-sha256",
        worker_sha256,
    ]
    clean_env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    with tempfile.TemporaryDirectory(prefix="titan-official-transition-") as cwd:
        try:
            completed = subprocess.run(
                command,
                input=fixture_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=clean_env,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise OracleError(
                f"sterile worker exceeded timeout {timeout_seconds:.3f}s"
            ) from exc
    stdout = completed.stdout
    stderr = completed.stderr
    if len(stdout) > MAX_OUTPUT_BYTES or len(stderr) > MAX_OUTPUT_BYTES:
        raise OracleError("worker output exceeds protocol bound")
    stdout_text = stdout.decode("utf-8", errors="strict")
    stderr_text = stderr.decode("utf-8", errors="strict")
    if stderr_text:
        raise OracleError(f"worker wrote stderr: {stderr_text[:1000]!r}")
    if completed.returncode != 0:
        raise OracleError(
            f"worker exited {completed.returncode}; stdout={stdout_text[:2000]!r}"
        )
    if not stdout_text or not stdout_text.endswith("\n"):
        raise OracleError("worker must emit exactly one newline-terminated JSON object")
    if stdout_text.count("\n") != 1:
        raise OracleError("worker emitted extra stdout lines")
    try:
        payload = strict_loads(stdout_text)
    except Exception as exc:
        raise OracleError("worker stdout is not strict JSON") from exc
    return payload, stdout_text, stderr_text, completed.returncode


def _validate_worker_receipt(
    payload: Json,
    *,
    fixture_sha256: str,
    engine_blob: str,
    engine_sha256: str,
    worker_sha256: str,
) -> None:
    if not isinstance(payload, dict):
        raise OracleError("worker receipt must be an object")
    if payload.get("schema") != WORKER_SCHEMA:
        raise OracleError("worker receipt schema mismatch")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise OracleError("worker receipt source is missing")
    expected = {
        "engine_git_blob": engine_blob,
        "engine_sha256": engine_sha256,
        "worker_sha256": worker_sha256,
    }
    for key, want in expected.items():
        if source.get(key) != want:
            raise OracleError(f"worker source mismatch for {key}")
    if payload.get("fixture_sha256") != fixture_sha256:
        raise OracleError("worker fixture hash mismatch")
    if payload.get("engine_unchanged") is not True:
        raise OracleError("worker did not prove engine bytes unchanged")
    claimed = payload.get("receipt_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise OracleError("worker receipt hash is missing or malformed")
    unhashed = dict(payload)
    del unhashed["receipt_sha256"]
    if semantic_hash(unhashed) != claimed:
        raise OracleError("worker receipt hash mismatch")
    _assert_finite(payload)


def run_fixture(
    *,
    engine_path: Path,
    worker_path: Path,
    fixture: Json,
    python_executable: Path | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Json:
    """Run one fixture in a sterile worker and return a verified envelope."""
    _validate_fixture_shape(fixture)
    fixture_bytes = canonical_bytes(fixture)
    if len(fixture_bytes) > MAX_INPUT_BYTES:
        raise OracleError("fixture exceeds input byte bound")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or timeout_seconds > 120:
        raise OracleError("timeout must be finite and in (0,120]")

    engine, engine_bytes = _bound_regular_file(engine_path, label="engine")
    expected_parts = EXPECTED_ENGINE_REL.parts
    if tuple(engine.parts[-len(expected_parts):]) != expected_parts:
        raise OracleError(
            f"engine path must end with {EXPECTED_ENGINE_REL.as_posix()}"
        )
    observed_blob = git_blob_sha(engine_bytes)
    if observed_blob != EXPECTED_ENGINE_GIT_BLOB:
        raise OracleError(
            f"engine Git blob mismatch: expected {EXPECTED_ENGINE_GIT_BLOB}, "
            f"observed {observed_blob}"
        )
    worker, worker_bytes = _bound_regular_file(worker_path, label="worker")
    launcher, launcher_bytes = _bound_regular_file(
        Path(__file__), label="launcher"
    )
    python_path = Path(python_executable or sys.executable).resolve(strict=True)
    if not python_path.is_file():
        raise OracleError("python executable is not a file")

    fixture_sha = sha256_bytes(fixture_bytes)
    engine_sha = sha256_bytes(engine_bytes)
    worker_sha = sha256_bytes(worker_bytes)
    payload, _stdout, _stderr, _returncode = _invoke_worker(
        python_executable=python_path,
        worker=worker,
        engine=engine,
        engine_blob=observed_blob,
        worker_sha256=worker_sha,
        fixture_bytes=fixture_bytes,
        timeout_seconds=timeout_seconds,
    )
    _validate_worker_receipt(
        payload,
        fixture_sha256=fixture_sha,
        engine_blob=observed_blob,
        engine_sha256=engine_sha,
        worker_sha256=worker_sha,
    )

    if engine.read_bytes() != engine_bytes:
        raise OracleError("engine bytes changed across worker execution")
    if worker.read_bytes() != worker_bytes:
        raise OracleError("worker bytes changed across execution")
    if launcher.read_bytes() != launcher_bytes:
        raise OracleError("launcher bytes changed across execution")

    envelope: dict[str, Json] = {
        "schema": SCHEMA,
        "fixture_sha256": fixture_sha,
        "source": {
            "engine_path_suffix": EXPECTED_ENGINE_REL.as_posix(),
            "engine_git_blob": observed_blob,
            "engine_sha256": engine_sha,
            "engine_bytes": len(engine_bytes),
            "worker_sha256": worker_sha,
            "worker_bytes": len(worker_bytes),
            "launcher_sha256": sha256_bytes(launcher_bytes),
            "launcher_bytes": len(launcher_bytes),
            "python_implementation": sys.implementation.name,
            "python_version": list(sys.version_info[:3]),
            "isolated_flags": ["-I", "-B"],
        },
        "worker_receipt": payload,
    }
    envelope["envelope_sha256"] = semantic_hash(envelope)
    return envelope


def validate_envelope(envelope: Json) -> None:
    if not isinstance(envelope, dict) or envelope.get("schema") != SCHEMA:
        raise OracleError("envelope schema mismatch")
    claimed = envelope.get("envelope_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise OracleError("envelope hash missing or malformed")
    body = dict(envelope)
    del body["envelope_sha256"]
    if semantic_hash(body) != claimed:
        raise OracleError("envelope hash mismatch")
    source = envelope.get("source")
    if not isinstance(source, dict):
        raise OracleError("envelope source missing")
    if source.get("engine_git_blob") != EXPECTED_ENGINE_GIT_BLOB:
        raise OracleError("envelope engine source mismatch")
    _assert_finite(envelope)


def write_json_atomic(path: Path, value: Json) -> None:
    """Create a result atomically without following a pre-existing target."""
    parent = path.parent.resolve(strict=True)
    target = (parent / path.name).resolve(strict=False)
    if target.parent != parent:
        raise OracleError("output path escapes its parent")
    if path.exists() or path.is_symlink():
        raise OracleError("output path already exists")
    data = canonical_bytes(value) + b"\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            temp.unlink(missing_ok=True)
        finally:
            raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()

    fixture_text = args.fixture.read_text(encoding="utf-8")
    fixture = strict_loads(fixture_text)
    envelope = run_fixture(
        engine_path=args.engine,
        worker_path=args.worker,
        fixture=fixture,
        timeout_seconds=args.timeout,
    )
    rendered = canonical_bytes(envelope) + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(rendered)
    else:
        write_json_atomic(args.output, envelope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
