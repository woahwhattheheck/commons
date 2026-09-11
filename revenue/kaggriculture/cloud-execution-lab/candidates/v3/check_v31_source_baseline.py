"""Run the six V3.1 source-level suites against an explicit isolated package tree.

The live V3.1 branch does not currently guarantee that its checked-in canonical export
matches ``V3-MANIFEST.json:base.sha256``.  This runner therefore deliberately requires
``--package-tree`` instead of implicitly calling ``build_v3.package_files()``.  That
keeps a stale or rebound canonical archive from turning the advertised default path into
an assertion failure before the suites run.

The selected tree is always copied to a temporary directory.  If its submission-mode
``r04_sale_window`` value is true, only the temporary copy is normalized to false before
the six historical source-baseline suites run.  The caller's package is never edited.
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
    """Reject the old implicit source path until the canonical base is reconciled."""
    raise SystemExit(
        "implicit source materialization is disabled: pass --package-tree PATH "
        "for an exact materialized/submission package tree"
    )


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
        required=True,
        help="exact materialized/submission-mode package tree to copy and test",
    )
    args = parser.parse_args(argv)
    return run(args.package_tree)


if __name__ == "__main__":
    raise SystemExit(main())
