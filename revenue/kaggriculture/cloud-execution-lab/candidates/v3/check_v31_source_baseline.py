"""Run the six V3 source-level integration suites against an isolated materialized tree.

By default this builds the current candidates/v3 source with build_v3.package_files().
``--package-tree`` can instead point at an already materialized or submission-mode tree.
The selected tree is always copied to a temporary directory; if its only submission-mode
difference is ``r04_sale_window=true``, that toggle is changed to false in the temporary
copy before tests run.  The caller's source/package is never edited.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SUITES = (
    "checks/test_v3_features.py",
    "checks/test_v3_l01.py",
    "checks/test_v3_r01.py",
    "checks/test_v3_r02.py",
    "checks/test_v3_r03.py",
    "checks/test_v3_r04.py",
)


def _materialize_source(target: Path) -> None:
    import build_v3

    files = build_v3.package_files()
    for name, blob in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise SystemExit("--package-tree must name a materialized package directory")
    shutil.copytree(source, target, dirs_exist_ok=True)


def _force_source_mode(target: Path) -> tuple[bool, dict]:
    config_path = target / "TITAN-CONFIG.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    original = bool(data.get("r04_sale_window", False))
    # These are the two measured V3.1 base mechanisms.  A tree that lacks them is not
    # the d5eca5b12 V3.1 baseline and should not silently receive a green receipt.
    for key in ("r04_sale_fertilizer", "r04_cattle_early"):
        if key not in data:
            raise SystemExit("not a V3.1 source tree: missing %s" % key)
    if original:
        data["r04_sale_window"] = False
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return original, data


def _assert_suites(target: Path) -> None:
    missing = [name for name in SUITES if not (target / name).is_file()]
    if missing:
        raise SystemExit("missing V3 source suites: " + ", ".join(missing))


def run(package_tree: Path | None = None) -> int:
    with tempfile.TemporaryDirectory(prefix="titan-v31-source-baseline-") as temp:
        target = Path(temp)
        if package_tree is None:
            _materialize_source(target)
            source_label = "current candidates/v3 source"
        else:
            _copy_tree(package_tree.resolve(), target)
            source_label = str(package_tree.resolve())

        submission_mode, data = _force_source_mode(target)
        _assert_suites(target)
        print("V3.1 SOURCE BASELINE")
        print("source:", source_label)
        print("temporary tree:", target)
        print("submission r04_sale_window was:", str(submission_mode).lower())
        print("test r04_sale_window is: false")
        print("r04_sale_fertilizer:", str(bool(data["r04_sale_fertilizer"])).lower())
        print("r04_cattle_early:", str(bool(data["r04_cattle_early"])).lower())
        print("suites:", len(SUITES))

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", *SUITES],
            cwd=target,
            env=env,
            check=False,
        )
        if completed.returncode:
            print("V3.1 SOURCE BASELINE FAIL", completed.returncode)
            return completed.returncode
        print("V3.1 SOURCE BASELINE PASS")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-tree",
        type=Path,
        help="copy and test an existing materialized/submission-mode tree instead of rebuilding source",
    )
    args = parser.parse_args(argv)
    return run(args.package_tree)


if __name__ == "__main__":
    raise SystemExit(main())
