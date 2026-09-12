# SPDX-License-Identifier: Apache-2.0
"""Exact submitted-V4 self-ablation for the E20 productive-detour expansion.

The submitted V3.1 and V4 packages both enable ``redundant_hire``.  Their helper
contract is the same, but V4 adds one behavior after the unchanged trailing-hire
physical certificate: before deleting a proven-redundant hire, it may protect
one worker and rewrite the producer-owned future route to execute a bounded
HARVEST -> DROP -> rejoin detour.

This research transform keeps the *exact submitted V4 helper prefix* and swaps
only that post-certificate tail for the exact submitted V3.1 deletion tail.
Therefore the counterfactual retains V4 parsing, prefix handling, physical
certificate, wages, route-switch guards, and every prior byte before the E20
branch.  It changes no config/default and never patches current V5 runtime.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

V31_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V4_COMMIT = "4af1113154e78c662780e6658cd920daac7902e3"
HELPER_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/reference/titan-current/"
    "redundant_hire.py"
)
V31_HELPER_GIT_BLOB = "4a0bf316290277607f520461442fa2d990a16780"
V4_HELPER_GIT_BLOB = "9ded2a9b636793df0511103da802bd3f26dbbb94"

V4_E20_START = (
    "    protected = 0; reserved: set[tuple[int, int]] = set(); detours = []\n"
)
V31_DELETE_TAIL_START = "    omitted = hires[-best:]\n"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def ablate_productive_detour(v4_source: bytes, v31_source: bytes) -> bytes:
    """Return exact-V4 semantics with only E20 route-detour protection removed."""
    if git_blob(v4_source) != V4_HELPER_GIT_BLOB:
        raise ValueError("submitted V4 redundant_hire.py drift")
    if git_blob(v31_source) != V31_HELPER_GIT_BLOB:
        raise ValueError("submitted V3.1 redundant_hire.py drift")

    v4 = v4_source.decode("utf-8")
    v31 = v31_source.decode("utf-8")
    if v4.count(V4_E20_START) != 1:
        raise ValueError("V4 E20 tail anchor drift")
    if v31.count(V31_DELETE_TAIL_START) != 1:
        raise ValueError("V3.1 deletion-tail anchor drift")

    prefix = v4[: v4.index(V4_E20_START)]
    deletion_tail = v31[v31.index(V31_DELETE_TAIL_START) :]
    result = (prefix + deletion_tail).encode("utf-8")
    compile(result, "<submitted-v4-e20-detour-off>", "exec")
    return result


def authority_receipt(v4_source: bytes, v31_source: bytes, output: bytes) -> dict:
    return {
        "submitted_v4_commit": V4_COMMIT,
        "submitted_v4_helper_git_blob": git_blob(v4_source),
        "submitted_v31_commit": V31_COMMIT,
        "submitted_v31_helper_git_blob": git_blob(v31_source),
        "ablation_helper_git_blob": git_blob(output),
        "changed_semantics": (
            "disable productive-detour hire protection and future-route rewrite; "
            "retain submitted-V4 trailing redundant-hire deletion"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v4-helper", required=True, type=Path)
    parser.add_argument("--v31-helper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    v4_source = args.v4_helper.read_bytes()
    v31_source = args.v31_helper.read_bytes()
    output = ablate_productive_detour(v4_source, v31_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    receipt = authority_receipt(v4_source, v31_source, output)
    for key in sorted(receipt):
        print(f"{key}={receipt[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
