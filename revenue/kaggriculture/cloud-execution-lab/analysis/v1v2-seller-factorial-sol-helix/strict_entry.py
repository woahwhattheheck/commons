# SPDX-License-Identifier: Apache-2.0
"""Root-owned generated entrypoint and runtime alias rejection."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from strict_types import ARMS, HEX64, AdmissionError, _is_int, _require_hex


def bound_entry_source(expected: Mapping[str, Any], arm: str) -> str:
    """Generate a closure guard that rejects module-cache and root escapes."""
    if arm not in ARMS:
        raise AdmissionError(f"unknown arm: {arm}")
    expected_sha = _require_hex(expected.get("sha256"), HEX64, "closure sha256")
    files = expected.get("files")
    total = expected.get("bytes")
    if not _is_int(files) or files <= 0 or not _is_int(total) or total <= 0:
        raise AdmissionError("closure files/bytes must be positive literal integers")
    return f'''# SPDX-License-Identifier: Apache-2.0
"""Generated root-owned entrypoint for factorial arm {arm}."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

_EXPECTED_SHA256 = {expected_sha!r}
_EXPECTED_FILES = {files}
_EXPECTED_BYTES = {total}
_ROOT = Path(__file__).resolve().parent


def _ignored(relative: Path) -> bool:
    return (any(part in {{"__pycache__", ".pytest_cache"}} for part in relative.parts)
            or relative.suffix in {{".pyc", ".pyo"}})


def _closure() -> tuple[str, int, int]:
    digest = hashlib.sha256(); files = 0; total = 0
    for path in sorted(_ROOT.rglob("*"), key=lambda item: item.relative_to(_ROOT).as_posix()):
        relative_path = path.relative_to(_ROOT); relative = relative_path.as_posix()
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in factorial closure: {{relative}}")
        if path.is_dir() or relative == "bound_entry.py" or _ignored(relative_path):
            continue
        if not path.is_file():
            raise RuntimeError(f"non-regular factorial closure member: {{relative}}")
        payload = path.read_bytes(); content_sha = hashlib.sha256(payload).digest()
        digest.update(relative.encode("utf-8") + b"\\0" + content_sha)
        files += 1; total += len(payload)
    return digest.hexdigest(), files, total


_actual = _closure(); _expected = (_EXPECTED_SHA256, _EXPECTED_FILES, _EXPECTED_BYTES)
if _actual != _expected:
    raise RuntimeError(f"factorial closure mismatch: expected={{_expected}} actual={{_actual}}")
for _name in ("candidate", "scheduler"):
    if _name in sys.modules:
        raise RuntimeError(f"preloaded factorial dependency forbidden: {{_name}}")
sys.path.insert(0, str(_ROOT))
try:
    import candidate as _candidate
    import scheduler as _scheduler
finally:
    try:
        sys.path.remove(str(_ROOT))
    except ValueError:
        pass
for _name, _module, _expected_name in (
    ("candidate", _candidate, "candidate.py"),
    ("scheduler", _scheduler, "scheduler.py"),
):
    _origin = Path(getattr(_module, "__file__", "")).resolve(strict=True)
    if _origin != (_ROOT / _expected_name).resolve(strict=True):
        raise RuntimeError(f"factorial dependency escaped bound root: {{_name}}={{_origin}}")
agent = _candidate.agent
if not callable(agent):
    raise RuntimeError("bound factorial agent is not callable")
'''


def _source_pythonpath() -> str:
    """Return the same root-module search surface used by the HELIX runner."""
    here = Path(__file__).resolve().parent
    lab = here.parents[1]
    if not (lab / "build_integrated.py").is_file():
        return ""
    if str(lab) not in sys.path:
        sys.path.insert(0, str(lab))
    from build_integrated import source_files  # type: ignore

    ordered = [lab]
    seen = {lab}
    for member, source in source_files().items():
        if Path(member).parent != Path("."):
            continue
        origin = (lab / source).resolve(strict=True)
        if origin.parent not in seen:
            seen.add(origin.parent)
            ordered.append(origin.parent)
    return os.pathsep.join(str(path) for path in ordered)


def verify_entry_runtime(entry: Path) -> dict[str, str]:
    """Prove clean import ownership and reject a preloaded candidate alias."""
    entry = Path(entry).resolve(strict=True)
    pythonpath = os.pathsep.join(p for p in (str(entry.parent), _source_pythonpath()) if p)
    clean_code = (
        "import importlib.util,json,pathlib,sys\n"
        f"p=pathlib.Path({str(entry)!r})\n"
        "s=importlib.util.spec_from_file_location('_vernier_clean',p)\n"
        "assert s is not None and s.loader is not None\n"
        "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)\n"
        "print(json.dumps({'candidate':str(pathlib.Path(sys.modules['candidate'].__file__).resolve()),"
        "'scheduler':str(pathlib.Path(sys.modules['scheduler'].__file__).resolve())},sort_keys=True))\n"
    )
    alias_code = (
        "import importlib.util,pathlib,sys,types\n"
        "x=types.ModuleType('candidate');x.__file__='/tmp/external-candidate.py';x.agent=lambda *a,**k:{}\n"
        "sys.modules['candidate']=x\n"
        f"p=pathlib.Path({str(entry)!r})\n"
        "s=importlib.util.spec_from_file_location('_vernier_alias',p)\n"
        "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)\n"
    )
    env = {
        "PATH": os.defpath,
        "HOME": str(entry.parent),
        "LANG": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": pythonpath,
    }
    clean = subprocess.run(
        [sys.executable, "-B", "-c", clean_code],
        cwd=entry.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if clean.returncode != 0:
        raise AdmissionError(f"bound entry clean import failed: {(clean.stderr or clean.stdout)[-1200:]}")
    try:
        origins = json.loads(clean.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise AdmissionError("bound entry did not report owned module origins") from exc
    expected = {
        "candidate": str((entry.parent / "candidate.py").resolve(strict=True)),
        "scheduler": str((entry.parent / "scheduler.py").resolve(strict=True)),
    }
    if origins != expected:
        raise AdmissionError(f"bound entry imported outside closure: {origins}")
    alias_probe = subprocess.run(
        [sys.executable, "-B", "-c", alias_code],
        cwd=entry.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if alias_probe.returncode == 0 or "preloaded factorial dependency forbidden" not in alias_probe.stderr:
        raise AdmissionError("bound entry accepts a preloaded candidate module")
    return origins

