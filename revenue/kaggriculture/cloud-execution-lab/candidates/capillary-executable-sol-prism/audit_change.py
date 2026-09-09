# SPDX-License-Identifier: Apache-2.0
"""Exact-source audit for the SOL-PRISM Capillary executable carrier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
REPO = KAG.parents[1]
WORKFLOW = REPO / ".github/workflows/titan-capillary-executable-sol-prism.yml"
EXPECTED_PARENT_HEAD = "68318e3da2af99f570c9e4d91029ad22d7a995e2"

EXPECTED_DELTA = {
    ".github/workflows/titan-capillary-executable-sol-prism.yml",
    "revenue/kaggriculture/cloud-execution-lab/candidates/"
    "capillary-executable-sol-prism/README.md",
    "revenue/kaggriculture/cloud-execution-lab/candidates/"
    "capillary-executable-sol-prism/audit_change.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/"
    "capillary-executable-sol-prism/candidate.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/"
    "capillary-executable-sol-prism/carrier_smoke.py",
}

SOURCE_BLOBS = {
    "revenue/kaggriculture/cloud-execution-lab/capillary_main.py":
        "e545a65d99f81f7982ee70fd4c336b78ad957afc",
    "revenue/kaggriculture/cloud-execution-lab/titan_capillary.py":
        "afbfb0859d7a3219d2f3e5c4178d72c128f31911",
    "revenue/kaggriculture/cloud-execution-lab/jit_seed_order_rail.py":
        "f5d2c3775bc527ef7f950a850eac8036bd71e865",
    "revenue/kaggriculture/cloud-execution-lab/jit_seed_staging.py":
        "e1cf2485ab869cf3c6f5eec455b0a25f6aeaa505",
    "revenue/kaggriculture/cloud-execution-lab/TITAN-CONFIG.json":
        "3a3bef83899d3010fad623b628d9e95d9978111b",
    "revenue/kaggriculture/cloud-execution-lab/scheduler.py":
        "a483b24dd72b580d7d8811636b54d2d44f391575",
    "revenue/kaggriculture/cloud-execution-lab/build_integrated.py":
        "05994d946885ff0fe2a2ce77439fd335174900aa",
    "revenue/kaggriculture/cloud-execution-lab/runtime/integrated-selected/"
    "CURRENT-ARCHIVE.json":
        "8a9023bb85447f0aad088699ecf7f0a03b808201",
    "revenue/kaggriculture/cloud-eval/evaluate.py":
        "077feb2208b6e0c1727835eb4f8089709bf67f3b",
    "revenue/kaggriculture/20260907-offline-agent/evaluate.py":
        "23948e10cfc3d32f46c9abb1321b0d8fc8db21d5",
}

EXPECTED_ARCHIVE_RECEIPT = {
    "path": "exports/titan-current.tar.gz",
    "entrypoint": "main.py::agent",
    "config": "TITAN-CONFIG.json",
    "sha256": "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86",
    "bytes": 427870,
    "runtime_files": 109,
    "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
    "source_manifest_sha256":
        "1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083",
}


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def require_regular(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"required source is not a regular file: {path}")


def verify_parent_and_delta() -> dict[str, Any]:
    git("cat-file", "-e", f"{EXPECTED_PARENT_HEAD}^{{commit}}")
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_PARENT_HEAD, "HEAD"],
        cwd=REPO,
    )
    if result.returncode != 0:
        raise RuntimeError("repair head is not descended from the reviewed parent")
    status_rows = [
        row.split("\t", 1)
        for row in git("diff", "--name-status", EXPECTED_PARENT_HEAD, "HEAD").splitlines()
        if row
    ]
    if any(len(row) != 2 or row[0] != "A" for row in status_rows):
        raise RuntimeError(f"repair is not additive-only: {status_rows}")
    paths = {row[1] for row in status_rows}
    if paths != EXPECTED_DELTA:
        raise RuntimeError(
            f"unexpected repair path delta; missing={sorted(EXPECTED_DELTA-paths)}, "
            f"extra={sorted(paths-EXPECTED_DELTA)}"
        )
    return {
        "parent": EXPECTED_PARENT_HEAD,
        "head": git("rev-parse", "HEAD"),
        "paths": sorted(paths),
        "all_additive": True,
    }


def verify_sources() -> dict[str, Any]:
    observed: dict[str, Any] = {}
    for relative, expected in SOURCE_BLOBS.items():
        path = REPO / relative
        require_regular(path)
        actual = git_blob_sha1(path)
        if actual != expected:
            raise RuntimeError(
                f"source drift for {relative}: expected {expected}, got {actual}"
            )
        observed[relative] = {
            "git_blob": actual,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }

    archive_receipt_path = (
        LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
    )
    archive_receipt = json.loads(archive_receipt_path.read_text(encoding="utf-8"))
    if archive_receipt != EXPECTED_ARCHIVE_RECEIPT:
        raise RuntimeError("canonical archive receipt drift")
    archive = LAB / archive_receipt["path"]
    require_regular(archive)
    if (
        archive.stat().st_size != archive_receipt["bytes"]
        or sha256(archive) != archive_receipt["sha256"]
    ):
        raise RuntimeError("canonical archive bytes differ from its exact receipt")

    scheduler = (LAB / "scheduler.py").read_text(encoding="utf-8")
    build = (LAB / "build_integrated.py").read_text(encoding="utf-8")
    if "from observed_clone import detached_json_value" not in scheduler:
        raise RuntimeError("lazy runtime dependency witness drift")
    if (
        "mapping['observed_clone.py']='../cloud-runtime-pulse/observed_clone.py'"
        not in build
    ):
        raise RuntimeError("canonical observed_clone source-map witness drift")
    return {
        "files": observed,
        "archive": archive_receipt,
        "lazy_dependency": "scheduler -> observed_clone",
        "mapped_source": "../cloud-runtime-pulse/observed_clone.py",
    }


def verify_repair_surface() -> dict[str, Any]:
    candidate = HERE / "candidate.py"
    smoke = HERE / "carrier_smoke.py"
    audit = HERE / "audit_change.py"
    readme = HERE / "README.md"
    for path in (candidate, smoke, audit, readme, WORKFLOW):
        require_regular(path)

    candidate_text = candidate.read_text(encoding="utf-8")
    smoke_text = smoke.read_text(encoding="utf-8")
    workflow_text = WORKFLOW.read_text(encoding="utf-8")

    required_candidate_needles = [
        "def _materialize_private_runtime(",
        "def _install_overlays(",
        "def _assert_private_runtime_modules(",
        "_ARENA_ROOT / \"capillary_main.py\"",
        "EXPECTED_ARCHIVE_SHA256",
        "EXPECTED_SOURCE_MANIFEST_SHA256",
        "jit_seed_staging.py",
        "jit_seed_order_rail.py",
        "titan_capillary.py",
        "capillary_main.py",
    ]
    for needle in required_candidate_needles:
        if needle not in candidate_text:
            raise RuntimeError(f"candidate carrier seam missing: {needle}")
    if "sys.path.insert(0, str(LAB" in candidate_text:
        raise RuntimeError("candidate reintroduced mutable repository PYTHONPATH")
    for expected in SOURCE_BLOBS.values():
        if expected in {
            SOURCE_BLOBS[
                "revenue/kaggriculture/cloud-execution-lab/capillary_main.py"
            ],
            SOURCE_BLOBS[
                "revenue/kaggriculture/cloud-execution-lab/titan_capillary.py"
            ],
            SOURCE_BLOBS[
                "revenue/kaggriculture/cloud-execution-lab/jit_seed_order_rail.py"
            ],
            SOURCE_BLOBS[
                "revenue/kaggriculture/cloud-execution-lab/jit_seed_staging.py"
            ],
        } and candidate_text.count(expected) != 1:
            raise RuntimeError(f"overlay blob pin cardinality drift: {expected}")

    required_smoke_needles = [
        'sys.executable, "-I", "-B", "-c"',
        'str(CANDIDATE.resolve()) + "::agent"',
        '"--episode-steps"',
        '"candidate_actor_calls"',
        '"compile_certified"',
        '"origins_inside_private_arena"',
        SOURCE_BLOBS["revenue/kaggriculture/cloud-eval/evaluate.py"],
        SOURCE_BLOBS[
            "revenue/kaggriculture/20260907-offline-agent/evaluate.py"
        ],
    ]
    for needle in required_smoke_needles:
        if needle not in smoke_text:
            raise RuntimeError(f"carrier smoke seam missing: {needle}")

    required_workflow_needles = [
        "audit_change.py",
        "carrier_smoke.py",
        "'test_jit_seed_staging'",
        "'test_jit_seed_order_rail'",
        "'test_capillary_lifecycle'",
        "'test_capillary_carrier_isolation'",
        "suite.countTestCases() != 70",
        "build_integrated.py --check",
        "git status --porcelain",
    ]
    for needle in required_workflow_needles:
        if needle not in workflow_text:
            raise RuntimeError(f"workflow gate missing: {needle}")

    return {
        "candidate": {
            "git_blob": git_blob_sha1(candidate),
            "sha256": sha256(candidate),
            "bytes": candidate.stat().st_size,
        },
        "carrier_smoke": {
            "git_blob": git_blob_sha1(smoke),
            "sha256": sha256(smoke),
            "bytes": smoke.stat().st_size,
        },
        "audit": {
            "git_blob": git_blob_sha1(audit),
            "sha256": sha256(audit),
            "bytes": audit.stat().st_size,
        },
        "readme": {
            "git_blob": git_blob_sha1(readme),
            "sha256": sha256(readme),
            "bytes": readme.stat().st_size,
        },
        "workflow": {
            "git_blob": git_blob_sha1(WORKFLOW),
            "sha256": sha256(WORKFLOW),
            "bytes": WORKFLOW.stat().st_size,
        },
    }


def run() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "operation": "titan-capillary-executable-carrier-20260909-sol-prism-01",
        "boundary": (
            "source and executable-carrier admission only; no gameplay, score, "
            "promotion, provider, pointer, archive, or canonical mutation"
        ),
        "lineage": verify_parent_and_delta(),
        "source_custody": verify_sources(),
        "repair_surface": verify_repair_surface(),
        "decision": "PASS",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    result = run()
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
