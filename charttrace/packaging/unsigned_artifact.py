"""Receipt builder for the actual frozen ChartTrace executable.

This module never fabricates a PE image and never substitutes an in-process
Python launcher for executable evidence.  It accepts an already-built,
unsigned PyInstaller executable, launches that exact byte artifact in
headless mode, and emits hashes, a portable bundle, an SBOM, and truthful
remaining release gates.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4


PACKAGING_DIR = Path(__file__).resolve().parent
CHARTTRACE_DIR = PACKAGING_DIR.parent
ROOT = CHARTTRACE_DIR.parent
ARTIFACT_LABEL = "UNSIGNED_SYNTHETIC"
SIGNING_STATE = "unsigned"
SYNTHETIC_RELEASED = False
MINIMUM_FROZEN_EXE_BYTES = 1_000_000
PINNED_PYINSTALLER_VERSION = "6.22.2"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exclusive_text(path: Path, value: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _product_source_paths() -> Iterable[Path]:
    for package in ("app", "ui", "legal"):
        for path in sorted((CHARTTRACE_DIR / package).glob("*.py")):
            if not path.name.startswith("test_") and path.name != "ipc.py":
                yield path
    yield CHARTTRACE_DIR / "launcher.py"
    for name in (
        "build_manifest.json",
        "build_windows.ps1",
        "ChartTrace.spec",
        "ChartTrace.iss",
        "charttrace.manifest",
        "README.md",
        "unsigned_artifact.py",
        "unsigned_pe.py",
    ):
        yield PACKAGING_DIR / name


def hash_packaging_inputs() -> Dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _sha256(path)
        for path in _product_source_paths()
        if path.is_file()
    }


def _installed_version(distribution: str) -> Optional[str]:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _build_sbom(executable: Path, source_hashes: Dict[str, str]) -> Dict[str, object]:
    import tkinter

    components = [
        {
            "type": "application",
            "name": executable.name,
            "version": "1.1",
            "hashes": [{"alg": "SHA-256", "content": _sha256(executable)}],
        },
        {
            "type": "framework",
            "name": "CPython",
            "version": platform.python_version(),
        },
        {"type": "framework", "name": "Tcl", "version": str(tkinter.TclVersion)},
        {"type": "framework", "name": "Tk", "version": str(tkinter.TkVersion)},
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid4()}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "ChartTrace",
                "version": "1.1",
            },
            "tools": [
                {
                    "vendor": "PyInstaller",
                    "name": "PyInstaller",
                    "version": _installed_version("pyinstaller") or "unknown",
                }
            ],
        },
        "components": components,
        "properties": [
            {"name": "charttrace:artifact_label", "value": ARTIFACT_LABEL},
            {"name": "charttrace:signing_state", "value": SIGNING_STATE},
            {"name": "charttrace:production", "value": "false"},
            {"name": "charttrace:source_hash_count", "value": str(len(source_hashes))},
        ],
        "externalReferences": [],
    }


def run_frozen_smoke(
    executable: Path,
    data_dir: Path,
    startup_receipt: Path,
    *,
    timeout: int = 45,
) -> Dict[str, object]:
    executable = executable.resolve(strict=True)
    if startup_receipt.exists() or startup_receipt.is_symlink():
        raise FileExistsError("Startup receipt destination must be new.")
    command = [
        str(executable),
        "--headless",
        "--data-dir",
        str(data_dir),
        "--startup-receipt",
        str(startup_receipt),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=timeout,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": str(error),
            "startup": None,
            "exact_executable_match": False,
            "host_python_smoke_used": False,
        }
    startup = None
    if startup_receipt.is_file():
        startup = json.loads(startup_receipt.read_text(encoding="utf-8"))
    exact_match = bool(
        startup
        and startup.get("frozen") is True
        and Path(str(startup.get("process_executable", ""))).resolve()
        == executable
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-1000:],
        "stderr": completed.stderr[-1000:],
        "startup": startup,
        "exact_executable_match": exact_match,
        "host_python_smoke_used": False,
    }


def build_unsigned_artifact(
    executable_path: Path,
    dest_dir: Path,
    *,
    build_log: Optional[Path] = None,
    authenticode_status: Optional[str] = None,
) -> Dict[str, object]:
    executable_path = Path(executable_path).resolve(strict=True)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if executable_path.read_bytes()[:2] != b"MZ":
        raise ValueError("Frozen Windows executable is not a PE image.")
    if executable_path.stat().st_size < MINIMUM_FROZEN_EXE_BYTES:
        raise ValueError("Executable is too small to be the frozen ChartTrace app.")

    artifact_path = dest_dir / "ChartTrace-1.1-UNSIGNED_SYNTHETIC.exe"
    if artifact_path.exists() or artifact_path.is_symlink():
        raise FileExistsError("Artifact destination must be new.")
    shutil.copy2(executable_path, artifact_path)

    notice_path = dest_dir / "UNSIGNED_NOTICE.txt"
    _exclusive_text(
        notice_path,
        "ChartTrace 1.1 UNSIGNED_SYNTHETIC portable artifact.\n"
        "signing_state=unsigned; production=false; synthetic_released=false.\n"
        "This exact executable passed a same-host frozen headless smoke only.\n"
        "Clean-VM install, usability/accessibility, and Authenticode remain release gates.\n",
    )
    startup_receipt = dest_dir / "frozen-startup-receipt.json"
    smoke = run_frozen_smoke(
        artifact_path,
        dest_dir / "smoke-data",
        startup_receipt,
    )
    if (
        smoke.get("returncode") != 0
        or smoke.get("exact_executable_match") is not True
    ):
        raise RuntimeError(f"Frozen executable smoke failed: {smoke!r}")

    source_hashes = hash_packaging_inputs()
    executable_hash = _sha256(artifact_path)
    hash_sidecar = dest_dir / f"{artifact_path.name}.sha256"
    _exclusive_text(hash_sidecar, f"{executable_hash}  {artifact_path.name}\n")
    sbom_path = dest_dir / "ChartTrace-1.1.cdx.json"
    _exclusive_text(
        sbom_path,
        json.dumps(
            _build_sbom(artifact_path, source_hashes),
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    manifest_path = PACKAGING_DIR / "build_manifest.json"
    bundle_path = dest_dir / "ChartTrace-1.1-UNSIGNED_SYNTHETIC.zip"
    if bundle_path.exists() or bundle_path.is_symlink():
        raise FileExistsError("Portable bundle destination must be new.")
    with zipfile.ZipFile(bundle_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(artifact_path, arcname=artifact_path.name)
        archive.write(notice_path, arcname=notice_path.name)
        archive.write(sbom_path, arcname=sbom_path.name)
        archive.write(startup_receipt, arcname=startup_receipt.name)
        archive.write(hash_sidecar, arcname=hash_sidecar.name)
        archive.write(manifest_path, arcname="build_manifest.json")

    receipt = {
        "application": "ChartTrace",
        "application_version": "1.1",
        "artifact_label": ARTIFACT_LABEL,
        "signing_state": SIGNING_STATE,
        "production": False,
        "synthetic_released": SYNTHETIC_RELEASED,
        "package_state": "actual-frozen-executable-built-and-host-smoked",
        "windows_executable_kind": "pyinstaller-onefile-frozen-application",
        "windows_executable_path": str(artifact_path),
        "windows_executable_size_bytes": artifact_path.stat().st_size,
        "windows_executable_sha256": executable_hash,
        "windows_executable_sha256_sidecar": str(hash_sidecar),
        "exact_executable_launched": True,
        "host_python_smoke_used": False,
        "same_host_windows_smoke": sys.platform.startswith("win"),
        "clean_vm_verified": False,
        "windows_clean_vm": "NOT_VERIFIED_THIS_WINDOWS_HOST",
        "installer_built": False,
        "installer_lifecycle_verified": False,
        "authenticode_status": authenticode_status,
        "unsigned_state_verified": authenticode_status == "NotSigned",
        "authenticode_verified": False,
        "ux_accessibility_verified": False,
        "host_platform": platform.platform(),
        "python_version": platform.python_version(),
        "pyinstaller_version": _installed_version("pyinstaller"),
        "portable_bundle_path": str(bundle_path),
        "portable_bundle_sha256": _sha256(bundle_path),
        "sbom_path": str(sbom_path),
        "sbom_sha256": _sha256(sbom_path),
        "startup_receipt_path": str(startup_receipt),
        "startup_receipt_sha256": _sha256(startup_receipt),
        "source_hashes": source_hashes,
        "build_log_path": str(build_log) if build_log is not None else None,
        "build_log_sha256": (
            _sha256(Path(build_log))
            if build_log is not None and Path(build_log).is_file()
            else None
        ),
        "smoke": smoke,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = dest_dir / "unsigned-artifact-receipt.json"
    _exclusive_text(
        receipt_path,
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    )
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha256"] = _sha256(receipt_path)
    return receipt


def required_input_paths() -> List[str]:
    return [
        path.relative_to(ROOT).as_posix()
        for path in _product_source_paths()
        if path.is_file()
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Receipt the actual frozen unsigned ChartTrace executable."
    )
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--build-log", type=Path, default=None)
    parser.add_argument("--authenticode-status", default=None)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    options = _build_parser().parse_args(argv)
    receipt = build_unsigned_artifact(
        options.exe,
        options.dest,
        build_log=options.build_log,
        authenticode_status=options.authenticode_status,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

