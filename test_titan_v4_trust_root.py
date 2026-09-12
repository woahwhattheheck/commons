#!/usr/bin/env python3
"""Regress Titan V4 trust-root custody, including pre-plumbing candidates.

Measured failure: workflow-custody on pull/12638 at
4b3af98f93fe629f2fc9a9f582ae29b9cbd2de5a exited 1 with
"candidate is missing .github/workflows/titan-v4-plumbing.yml" even though
canonical BASE 465f4263da1c98acf78889d67cdd21b61dbba145 also lacks that
path. #12620 owns introducing exact blob
2a1800c02d2a4c11293bdccc7914ab8f6fd93321; later serial-queue gameplay PRs
must not be forced to mint a sibling plumbing carrier.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
HELPER = ROOT / "host" / "titan_v4_trust_root.py"
WORKFLOW = ROOT / ".github" / "workflows" / "titan-v4-trust-root.yml"
APPROVED = "2a1800c02d2a4c11293bdccc7914ab8f6fd93321"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_helper_self_test() -> None:
    subprocess.check_call([sys.executable, str(HELPER), "--self-test"])


def test_workflow_pins_frozen_blob_and_preplumbing_road() -> None:
    text = _read(WORKFLOW)
    if f"APPROVED_WORKFLOW_BLOB: {APPROVED}" not in text:
        raise SystemExit("trust-root must keep the frozen plumbing blob pin")
    if "host/titan_v4_trust_root.py" not in text:
        raise SystemExit("trust-root must invoke the Git-data-only helper")
    if "candidate is missing" in text:
        raise SystemExit("unconditional missing-workflow fail is the measured false red")
    if "pull_request_target" not in text:
        raise SystemExit("trust-root must stay base-owned pull_request_target")
    if "ref: main" not in text:
        raise SystemExit("trust-root must checkout trusted main, never PR HEAD")
    if "persist-credentials: false" not in text:
        raise SystemExit("trust-root must not persist credentials")


def main() -> int:
    test_helper_self_test()
    test_workflow_pins_frozen_blob_and_preplumbing_road()
    print("ok   test_titan_v4_trust_root.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
