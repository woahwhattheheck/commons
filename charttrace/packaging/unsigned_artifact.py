"""Build an unsigned ChartTrace artifact receipt.

This host may not be Windows. The receipt stays truthful: no invented
signature, production stays false, and a generated PE stub is labeled
UNSIGNED_SYNTHETIC. Clean-VM launch is recorded only when this host can
actually run the image.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Dict, List

from charttrace.launcher import main as launcher_main
from charttrace.packaging.unsigned_pe import write_unsigned_pe


PACKAGING_DIR = Path(__file__).resolve().parent
CHARTTRACE_DIR = PACKAGING_DIR.parent
ROOT = CHARTTRACE_DIR.parent
ARTIFACT_LABEL = "UNSIGNED_SYNTHETIC"
SIGNING_STATE = "unsigned"
SYNTHETIC_RELEASED = False


INPUT_FILES = (
    PACKAGING_DIR / "build_manifest.json",
    PACKAGING_DIR / "build_windows.ps1",
    PACKAGING_DIR / "ChartTrace.spec",
    PACKAGING_DIR / "ChartTrace.iss",
    PACKAGING_DIR / "charttrace.manifest",
    PACKAGING_DIR / "README.md",
    PACKAGING_DIR / "unsigned_pe.py",
    CHARTTRACE_DIR / "launcher.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_packaging_inputs() -> Dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _sha256(path)
        for path in INPUT_FILES
        if path.is_file()
    }


def run_headless_smoke(data_dir: Path) -> Dict[str, object]:
    command = ["charttrace.launcher.main", "--headless", "--data-dir", str(data_dir)]
    output = StringIO()
    try:
        with redirect_stdout(output):
            returncode = launcher_main(["--headless", "--data-dir", str(data_dir)])
        stdout = output.getvalue().strip()
        payload = {
            "command": command,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": "",
        }
        if returncode == 0 and stdout:
            payload["startup"] = json.loads(stdout)
        return payload
    except Exception as error:  # noqa: BLE001 - smoke receipt must stay truthful
        return {
            "command": command,
            "returncode": 1,
            "stdout": output.getvalue().strip(),
            "stderr": str(error),
        }


def _wine_smoke(pe_path: Path) -> Dict[str, object]:
    wine = shutil.which("wine")
    if wine is None:
        return {
            "ran": False,
            "reason": "wine_not_on_path",
            "returncode": None,
        }
    try:
        completed = subprocess.run(
            [wine, str(pe_path)],
            check=False,
            capture_output=True,
            timeout=20,
            text=True,
        )
        return {
            "ran": True,
            "command": [wine, str(pe_path)],
            "returncode": completed.returncode,
            "stdout": completed.stdout[-500:],
            "stderr": completed.stderr[-500:],
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "ran": True,
            "reason": str(error),
            "returncode": 1,
        }


def build_unsigned_artifact(dest_dir: Path) -> Dict[str, object]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    input_hashes = hash_packaging_inputs()
    pe_path = dest_dir / "ChartTrace-1.1-UNSIGNED_SYNTHETIC.exe"
    pe_meta = write_unsigned_pe(pe_path)
    bundle_path = dest_dir / "ChartTrace-1.1-UNSIGNED_SYNTHETIC.zip"
    with dest_dir.joinpath("UNSIGNED_NOTICE.txt").open("w", encoding="utf-8") as notice:
        notice.write(
            "ChartTrace v1.1 UNSIGNED_SYNTHETIC artifact.\n"
            "signing_state=unsigned. Not a production build. "
            "No code signature. The included PE32 stub is unsigned "
            "and is not a clean-VM Windows proof by itself.\n"
        )
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in INPUT_FILES:
            if path.is_file():
                archive.write(path, arcname=path.relative_to(ROOT).as_posix())
        archive.write(pe_path, arcname=pe_path.name)
        archive.write(
            dest_dir / "UNSIGNED_NOTICE.txt",
            arcname="UNSIGNED_NOTICE.txt",
        )
    smoke = run_headless_smoke(dest_dir / "smoke-data")
    wine_smoke = _wine_smoke(pe_path)
    host_is_windows = sys.platform.startswith("win")
    if host_is_windows:
        clean_vm = (
            "RAN_HEADLESS_SMOKE_ON_THIS_WINDOWS_HOST"
            if smoke.get("returncode") == 0
            else "SMOKE_FAILED"
        )
        windows_clean_vm = "THIS_HOST_IS_WINDOWS"
    elif wine_smoke.get("ran") and wine_smoke.get("returncode") == 0:
        clean_vm = "RAN_WINE_SMOKE_ON_THIS_HOST"
        windows_clean_vm = "WINE_SMOKE_ONLY_NOT_CLEAN_VM"
    else:
        clean_vm = (
            "RAN_HEADLESS_SMOKE_ON_THIS_HOST"
            if smoke.get("returncode") == 0
            else "SMOKE_FAILED"
        )
        windows_clean_vm = "NOT_AVAILABLE_ON_THIS_HOST"
    receipt = {
        "application": "ChartTrace",
        "application_version": "1.1",
        "artifact_label": ARTIFACT_LABEL,
        "signing_state": SIGNING_STATE,
        "production": False,
        "synthetic_released": SYNTHETIC_RELEASED,
        "windows_pe_built": True,
        "windows_pe_kind": "unsigned_pe32_stub",
        "windows_pe_path": pe_meta["path"],
        "windows_pe_sha256": pe_meta["sha256"],
        "clean_vm_launch": clean_vm,
        "windows_clean_vm": windows_clean_vm,
        "host_platform": platform.platform(),
        "bundle_path": str(bundle_path),
        "bundle_sha256": _sha256(bundle_path),
        "input_hashes": input_hashes,
        "windows_pe_command": ".\\charttrace\\packaging\\build_windows.ps1",
        "smoke": smoke,
        "wine_smoke": wine_smoke,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = dest_dir / "unsigned-artifact-receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha256"] = _sha256(receipt_path)
    return receipt


def required_input_paths() -> List[str]:
    return [path.relative_to(ROOT).as_posix() for path in INPUT_FILES]
