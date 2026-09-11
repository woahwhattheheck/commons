"""Run the six V3.1 source-level suites against an explicit isolated package tree.

The live V3.1 branch does not currently guarantee that its checked-in canonical export
matches ``V3-MANIFEST.json:base.sha256``.  This runner therefore deliberately requires
``--package-tree`` instead of implicitly calling ``build_v3.package_files()``.

The explicit tree is copied to a temporary directory first, preserving symbolic links.
That exact temporary copy is then verified against this source tree's committed
``FILES.json`` before any normalization or test executes, avoiding a verify-then-copy
TOCTOU gap.  Submission mode may differ only in
``TITAN-CONFIG.json:r04_sale_window=true``; that config is normalized in memory to source
mode for its recorded hash.  The caller's package is never edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
FILES_MANIFEST = HERE / "FILES.json"
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


def _sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _materialize_source(target: Path) -> None:
    """Reject the old implicit source path until the canonical base is reconciled."""
    raise SystemExit(
        "implicit source materialization is disabled: pass --package-tree PATH "
        "for an exact materialized/submission package tree"
    )


def _sale_window_value(data: object) -> bool:
    """Return the exact JSON boolean submission-mode flag or fail closed."""
    if not isinstance(data, dict):
        raise SystemExit("TITAN-CONFIG.json must contain a JSON object")
    if "r04_sale_window" not in data:
        raise SystemExit("TITAN-CONFIG.json is missing r04_sale_window")
    value = data["r04_sale_window"]
    if value is True:
        return True
    if value is False:
        return False
    raise SystemExit("TITAN-CONFIG.json r04_sale_window must be a JSON boolean")


def _normalized_config_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    submission_mode = _sale_window_value(data)
    if submission_mode:
        data["r04_sale_window"] = False
        return (json.dumps(data, indent=2) + "\n").encode("utf-8")
    return raw


def _verify_package_tree(source: Path) -> None:
    if not source.is_dir():
        raise SystemExit("--package-tree must name a materialized package directory")
    links = [p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_symlink()]
    if links:
        raise SystemExit("package tree contains symbolic links: " + ", ".join(sorted(links)[:8]))

    recorded = json.loads(FILES_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(recorded, dict) or "TITAN-CONFIG.json" not in recorded:
        raise SystemExit("FILES.json is not a valid V3 package-file manifest")

    actual = {
        p.relative_to(source).as_posix(): p
        for p in source.rglob("*")
        if p.is_file()
    }
    missing = sorted(set(recorded) - set(actual))
    extra = sorted(set(actual) - set(recorded))
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing=" + ",".join(missing[:8]))
        if extra:
            parts.append("extra=" + ",".join(extra[:8]))
        raise SystemExit("package tree file-set mismatch: " + " ".join(parts))

    mismatches = []
    for name in sorted(recorded):
        path = actual[name]
        blob = _normalized_config_bytes(path) if name == "TITAN-CONFIG.json" else path.read_bytes()
        if _sha256(blob) != recorded[name]:
            mismatches.append(name)
    if mismatches:
        raise SystemExit("package tree hash mismatch: " + ", ".join(mismatches[:8]))

    print("V3 PACKAGE TREE VERIFIED", len(recorded), "files")


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise SystemExit("--package-tree must name a materialized package directory")
    # Preserve links rather than dereferencing them; verification rejects any link in
    # the exact temp tree that will be tested.
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)


def _force_source_mode(target: Path) -> tuple[bool, dict]:
    config_path = target / "TITAN-CONFIG.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    original = _sale_window_value(data)
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
    if package_tree is None:
        _materialize_source(Path("."))
    source = package_tree.resolve()

    with tempfile.TemporaryDirectory(prefix="titan-v31-source-baseline-") as temp:
        target = Path(temp)
        _copy_tree(source, target)
        _verify_package_tree(target)
        source_label = str(source)

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
        help="exact materialized/submission-mode package tree to copy, verify, and test",
    )
    args = parser.parse_args(argv)
    return run(args.package_tree)


if __name__ == "__main__":
    raise SystemExit(main())
