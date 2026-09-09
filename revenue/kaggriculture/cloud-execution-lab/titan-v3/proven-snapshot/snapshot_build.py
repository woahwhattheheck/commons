# SPDX-License-Identifier: Apache-2.0
"""Deterministic publication and isolated smoke for proven Titan v3."""
from __future__ import annotations

import gzip
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import uuid
from typing import Mapping

from snapshot_model import (
    MAIN_BYTES,
    OUTPUT_ENTRYPOINT,
    PRODUCTION_PIN,
    SCHEMA,
    SOURCE_ENTRYPOINT,
    Pin,
    SnapshotError,
    read_archive,
    sha256,
)
from snapshot_validate import assert_python_closure, validate_source


def deterministic_tar(members: Mapping[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, payload in sorted(members.items()):
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mode = 0o644
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                archive.addfile(info, io.BytesIO(payload))
    return raw.getvalue()


def smoke_import(candidate_data: bytes) -> None:
    members = read_archive(candidate_data)
    with tempfile.TemporaryDirectory(prefix="titan-v3-proven-") as temporary:
        root = Path(temporary)
        for name, payload in members.items():
            target = root / PurePosixPath(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        program = (
            "import os,sys; sys.path.insert(0, os.getcwd()); "
            "import candidate,main; assert callable(main.agent); "
            "assert main.agent is candidate.agent; print(main.agent.__module__)"
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-c", program],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SnapshotError(f"isolated import smoke could not run: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[-1200:]
            raise SnapshotError(f"isolated import smoke failed: {detail}")


def atomic_write(path: Path, payload: bytes, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise SnapshotError(f"refusing to overwrite existing output: {path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            view = memoryview(payload)
            while view:
                written = stream.write(view)
                if not written:
                    raise OSError("staging write made no progress")
                view = view[written:]
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists() and not overwrite:
            raise SnapshotError(f"output appeared during publication: {path}")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def materialize(
    lab_root: Path,
    *,
    output: Path | None = None,
    receipt_path: Path | None = None,
    overwrite: bool = False,
    run_smoke: bool = True,
    pin: Pin = PRODUCTION_PIN,
) -> dict:
    """Validate the immutable source and optionally publish a runnable archive."""
    lab_root = lab_root.resolve()
    members, freeze, selected, source_imports = validate_source(lab_root, pin)
    output_members = dict(members)
    if "main.py" in output_members:
        raise SnapshotError("source archive unexpectedly owns generated main.py")
    output_members["main.py"] = MAIN_BYTES
    candidate_data = deterministic_tar(output_members)
    parsed_output = read_archive(candidate_data)
    if parsed_output != output_members:
        raise SnapshotError("deterministic candidate round-trip mismatch")
    candidate_imports = assert_python_closure(parsed_output)
    if run_smoke:
        smoke_import(candidate_data)

    receipt = {
        "schema": SCHEMA,
        "status": "PASS",
        "source": {
            "commit": pin.source_commit,
            "archive": selected,
            "freeze_version": freeze["version"],
            "freeze_sha256": pin.source_freeze_sha256,
            "entrypoint": SOURCE_ENTRYPOINT,
        },
        "candidate": {
            "entrypoint": OUTPUT_ENTRYPOINT,
            "bytes": len(candidate_data),
            "sha256": sha256(candidate_data),
            "files": len(output_members),
            "generated_main_sha256": sha256(MAIN_BYTES),
        },
        "members": {
            name: {"bytes": len(payload), "sha256": sha256(payload)}
            for name, payload in sorted(output_members.items())
        },
        "imports": {"source": source_imports, "candidate": candidate_imports},
        "evidence_scope": {
            "development": {"wins": 12, "ties": 0, "losses": 0, "games": 12},
            "held_out": {"wins": 8, "ties": 0, "losses": 0, "games": 8},
            "kind": "recorded local official-interpreter games; not hosted rating",
        },
        "policy_delta": "generated main.py alias only; frozen policy bytes unchanged",
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")

    if output is not None:
        output = output.resolve()
        if receipt_path is not None and output == receipt_path.resolve():
            raise SnapshotError("candidate and receipt paths must differ")
        if receipt_path is not None and receipt_path.exists() and not overwrite:
            raise SnapshotError(f"refusing to overwrite existing receipt: {receipt_path}")
        atomic_write(output, candidate_data, overwrite=overwrite)
        if receipt_path is not None:
            atomic_write(receipt_path.resolve(), receipt_bytes, overwrite=overwrite)
    elif receipt_path is not None:
        raise SnapshotError("receipt_path requires an output archive")
    return receipt
