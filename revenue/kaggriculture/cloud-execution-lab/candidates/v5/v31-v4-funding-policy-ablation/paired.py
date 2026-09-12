#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Custody shell around the byte-identical funding-policy causal runner core.

The core keeps the 2x2 causal theorem unchanged. This shell seals the caller-owned
official-engine cache before execution and withholds every runner output path
from the caller until the complete panel has returned.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types

CORE_PAIRED_GIT_BLOB = "e99c030220641122fa9bd364098375feab96c33b"
ENGINE_BLOBS = {
    "kaggriculture.py": "3c202c7ee921da239356789e266b694635103fc4",
    "kaggriculture.json": "b354d06b742fe48402513792253f1a5c29366b20",
    "utils.py": "91c8822ee6201ba4a5a8416c7dbe34f95dd61c87",
}


def _git_blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load_core():
    path = Path(__file__).with_name("paired_core.py")
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"paired core must be an ordinary file: {path}")
    raw = path.read_bytes()
    actual = _git_blob_bytes(raw)
    if actual != CORE_PAIRED_GIT_BLOB:
        raise ValueError(
            f"paired core Git blob mismatch; expected {CORE_PAIRED_GIT_BLOB}, got {actual}"
        )
    module = types.ModuleType("funding_policy_paired_core")
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


_core = _load_core()
for _name, _value in vars(_core).items():
    if _name not in {"__name__", "__file__", "__package__", "__loader__", "__spec__"}:
        globals().setdefault(_name, _value)


def capture_engine_sources(engine_dir: Path, pins=None) -> dict[str, bytes]:
    """Single-read and Git-blob-authenticate every official engine authority."""
    pins = dict(ENGINE_BLOBS if pins is None else pins)
    root = Path(engine_dir)
    if root.is_symlink():
        raise ValueError(f"engine directory must not be a symlink: {root}")
    root = root.resolve(strict=True)
    if not root.is_dir() or not pins:
        raise ValueError("engine directory and pin set must be non-empty")
    captured = {}
    for name, expected in pins.items():
        if not isinstance(name, str) or Path(name).name != name or not name:
            raise ValueError(f"unsafe engine member name: {name!r}")
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"official engine member must be an ordinary file: {path}")
        raw = path.read_bytes()
        actual = _git_blob_bytes(raw)
        if actual != expected:
            raise ValueError(
                f"official engine source mismatch: {name}; expected {expected}, got {actual}"
            )
        captured[name] = raw
    return captured


def publish_private_engine_sources(captured: dict[str, bytes], destination: Path, pins=None) -> Path:
    """Create one private engine cache from already-authenticated captured bytes."""
    pins = dict(ENGINE_BLOBS if pins is None else pins)
    if set(captured) != set(pins):
        raise ValueError("captured engine member set does not match the authenticated pin set")
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(destination, 0o700)
    for name, expected in pins.items():
        raw = captured[name]
        if type(raw) is not bytes or _git_blob_bytes(raw) != expected:
            raise ValueError(f"captured engine bytes failed re-authentication: {name}")
        target = destination / name
        with target.open("xb") as stream:
            stream.write(raw)
        os.chmod(target, 0o600)
        if _git_blob_bytes(target.read_bytes()) != expected:
            raise ValueError(f"private engine publication changed authenticated bytes: {name}")
    return destination


def _argument(argv: list[str], option: str) -> str:
    prefix = option + "="
    for index, value in enumerate(argv[1:], 1):
        if value == option:
            if index + 1 >= len(argv):
                raise ValueError(f"missing value for {option}")
            return argv[index + 1]
        if value.startswith(prefix):
            return value[len(prefix):]
    raise ValueError(f"required argument missing: {option}")


def _replace_argument(argv: list[str], option: str, replacement: str) -> list[str]:
    result = list(argv)
    prefix = option + "="
    for index, value in enumerate(result[1:], 1):
        if value == option:
            if index + 1 >= len(result):
                raise ValueError(f"missing value for {option}")
            result[index + 1] = replacement
            return result
        if value.startswith(prefix):
            result[index] = prefix + replacement
            return result
    raise ValueError(f"required argument missing: {option}")


def _bind_custody_receipt(private_output: Path, captured: dict[str, bytes]) -> None:
    run_path = private_output / "run.json"
    if not run_path.is_file() or run_path.is_symlink():
        raise ValueError("completed core run did not publish an ordinary run.json")
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["execution_custody"] = {
        "mode": "private_engine_and_private_output_until_core_return",
        "core_runner_git_blob": CORE_PAIRED_GIT_BLOB,
        "engine_git_blobs": dict(ENGINE_BLOBS),
        "engine_sha256": {
            name: hashlib.sha256(raw).hexdigest() for name, raw in captured.items()
        },
        "caller_engine_reopened_after_capture": False,
        "caller_output_visible_during_execution": False,
    }
    temporary = run_path.with_suffix(run_path.suffix + ".custody.tmp")
    temporary.write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, run_path)


def publish_evidence(private_output: Path, public_output: Path) -> Path:
    """Publish only completed, non-symlink evidence after all execution has stopped."""
    private_output = Path(private_output).resolve(strict=True)
    public_output = Path(public_output)
    if public_output.exists() or public_output.is_symlink():
        raise FileExistsError(public_output)
    for path in private_output.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"refusing to publish symlink evidence: {path}")
    shutil.copytree(private_output, public_output)
    return public_output


def main() -> int:
    original_argv = list(sys.argv)
    caller_engine = Path(_argument(original_argv, "--engine-dir"))
    public_output = Path(_argument(original_argv, "--output")).resolve()
    if public_output.exists() or public_output.is_symlink():
        raise FileExistsError(public_output)
    output_parent = public_output.parent.resolve(strict=True)

    captured = capture_engine_sources(caller_engine)
    with tempfile.TemporaryDirectory(prefix="funding-custody-", dir=output_parent) as td:
        private_root = Path(td)
        os.chmod(private_root, 0o700)
        private_engine = publish_private_engine_sources(captured, private_root / "engine")
        private_output = private_root / "output"
        rewritten = _replace_argument(original_argv, "--engine-dir", str(private_engine))
        rewritten = _replace_argument(rewritten, "--output", str(private_output))
        previous_argv = sys.argv
        try:
            sys.argv = rewritten
            result = _core.main()
        finally:
            sys.argv = previous_argv
        if not private_output.is_dir():
            raise ValueError("core runner returned without a private evidence directory")
        _bind_custody_receipt(private_output, captured)
        publish_evidence(private_output, public_output)
        return result


if __name__ == "__main__":
    raise SystemExit(main())
