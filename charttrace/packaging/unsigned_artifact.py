"""Build an unsigned ChartTrace artifact receipt.

This host may not be Windows. The receipt stays truthful: no PE is invented,
signing_state remains unsigned, and production is false.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import zipfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Dict, List

from charttrace.launcher import main as launcher_main


PACKAGING_DIR = Path(__file__).resolve().parent
CHARTTRACE_DIR = PACKAGING_DIR.parent
ROOT = CHARTTRACE_DIR.parent
ARTIFACT_LABEL = "UNSIGNED_SYNTHETIC"
SIGNING_STATE = "unsigned"


INPUT_FILES = (
    PACKAGING_DIR / "build_manifest.json",
    PACKAGING_DIR / "build_windows.ps1",
    PACKAGING_DIR / "ChartTrace.spec",
    PACKAGING_DIR / "ChartTrace.iss",
    PACKAGING_DIR / "charttrace.manifest",
    PACKAGING_DIR / "README.md",
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


def build_unsigned_artifact(dest_dir: Path) -> Dict[str, object]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    input_hashes = hash_packaging_inputs()
    bundle_path = dest_dir / "ChartTrace-1.1-UNSIGNED_SYNTHETIC.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in INPUT_FILES:
            if path.is_file():
                archive.write(path, arcname=path.relative_to(ROOT).as_posix())
        archive.writestr(
            "UNSIGNED_NOTICE.txt",
            (
                "ChartTrace v1.1 UNSIGNED_SYNTHETIC artifact.\n"
                "signing_state=unsigned. Not a production build. "
                "No code signature. No Windows PE is implied by this zip.\n"
            ),
        )
    smoke = run_headless_smoke(dest_dir / "smoke-data")
    host_is_windows = sys.platform.startswith("win")
    receipt = {
        "application": "ChartTrace",
        "application_version": "1.1",
        "artifact_label": ARTIFACT_LABEL,
        "signing_state": SIGNING_STATE,
        "production": False,
        "windows_pe_built": False,
        "clean_vm_launch": (
            "RAN_HEADLESS_SMOKE_ON_THIS_HOST"
            if smoke.get("returncode") == 0
            else "SMOKE_FAILED"
        ),
        "windows_clean_vm": (
            "AVAILABLE" if host_is_windows else "NOT_AVAILABLE_ON_THIS_HOST"
        ),
        "host_platform": platform.platform(),
        "bundle_path": str(bundle_path),
        "bundle_sha256": _sha256(bundle_path),
        "input_hashes": input_hashes,
        "windows_pe_command": (
            ".\\charttrace\\packaging\\build_windows.ps1"
        ),
        "smoke": smoke,
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
