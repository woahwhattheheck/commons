#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prove both exact signed-build_v3 predecessor failures without network/gameplay."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest import mock


def load(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("v3_build_predecessor", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prove(build_path: Path) -> dict:
    module = load(build_path)
    report: dict[str, object] = {}
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "candidate"
        target.mkdir()
        stale = target / "sitecustomize.py"
        stale.write_text("raise RuntimeError('stale tree executed')\n", encoding="utf-8")
        with mock.patch.object(module, "package_files", return_value={"main.py": b"print('ok')\n"}):
            module.main(["--tree", str(target)])
        files = sorted(path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file())
        assert files == ["main.py", "sitecustomize.py"], files
        report["nonempty_merge"] = {
            "stale_survived": stale.exists(),
            "main_written": (target / "main.py").exists(),
            "files": files,
        }

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "candidate"
        target.mkdir()
        with mock.patch.object(module, "package_files", return_value={"../escape.py": b"ESCAPE\n"}):
            module.main(["--tree", str(target)])
        escaped = root / "escape.py"
        assert escaped.read_bytes() == b"ESCAPE\n"
        assert not any(target.iterdir())
        report["path_escape"] = {
            "escaped_file_exists": escaped.exists(),
            "target_files": [],
        }
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: prove_predecessor.py PATH/TO/build_v3.py")
    print(json.dumps(prove(Path(argv[1]).resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
