#!/usr/bin/env python3
"""Optimization-independent verifier for the SOL-BOUNDARY evidence handoff."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PATCH = ROOT / "evidence/canonical-input-closure.patch"
VALIDATION = ROOT / "evidence/validation.json"
PREDECESSOR = ROOT / "evidence/predecessor.json"
SOURCE_RECEIPT = ROOT / "evidence/source_receipt_stdout.txt"

EXPECTED_PATCH = "fe6e9b53c5a1546394e591f9657ce555551c057eb7e9d38d667c82227dd7ef59"
EXPECTED_PACKET = "f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728"
EXPECTED_ESCAPE = "b38483d1bcc364216241e43521a606e3eb97a19294828bcc4b9fdcba8fdcc61a"
EXPECTED_BUILDER = "48e5df9154d6a165ed6f29d0981bb1a25b2566bea6f0ca08ec18f97c75d41155"
EXPECTED_TEST = "a192c5fea7e73a0544ac2fc50097cd7aa5593be5980311256f17612b2034ba36"


def fail(message: str) -> None:
    raise SystemExit("EVIDENCE_INVALID: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    for path in (PATCH, VALIDATION, PREDECESSOR, SOURCE_RECEIPT):
        require(path.is_file(), "missing %s" % path.relative_to(ROOT))

    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    patch = PATCH.read_text(encoding="utf-8")

    require(sha256(PATCH) == EXPECTED_PATCH, "patch byte hash drift")
    require(validation.get("patch", {}).get("sha256") == EXPECTED_PATCH,
            "validation does not bind the exact patch")
    require(predecessor.get("input_packet", {}).get("sha256") == EXPECTED_PACKET,
            "authenticated packet identity drift")
    require(predecessor.get("input_packet", {}).get("slack_file_id") == "F0C0JPCAAQP",
            "authenticated packet file id drift")
    escape = predecessor.get("parent_escape_witness", {})
    require(escape.get("outside_exists_before_cleanup") is True,
            "parent-escape predecessor was not reproduced")
    require(escape.get("outside_sha256_before_cleanup") == EXPECTED_ESCAPE,
            "parent-escape witness byte identity drift")
    require(escape.get("package_files_returned_names") == [],
            "predecessor did not return the recorded successful empty package")

    require(validation.get("patched_files", {}).get("build_v3.py") == EXPECTED_BUILDER,
            "patched builder identity drift")
    require(validation.get("patched_files", {}).get(
        "source_checks/test_build_v3_closure.py") == EXPECTED_TEST,
        "source-contract identity drift")
    require(validation.get("preserved_outputs", {}).get("apply_v3.py_unchanged") is True,
            "apply_v3 preservation claim missing")
    require(validation.get("preserved_outputs", {}).get("FILES.json_unchanged") is True,
            "FILES.json preservation claim missing")

    checks = validation.get("validation", {})
    for mode in ("normal_python", "optimized_python"):
        require(checks.get(mode, {}).get("status") == "PASS", "%s is not PASS" % mode)
        require(checks.get(mode, {}).get("tests") == 8, "%s test cardinality drift" % mode)
    original = checks.get("original_with_successor_contracts", {})
    require(original.get("status") == "FAIL_AS_REQUIRED", "predecessor rejection drift")
    require(original.get("returncode") == 1, "predecessor return code drift")
    require(original.get("reported_errors") == 18, "predecessor error cardinality drift")
    require(checks.get("patch_applies_byte_exact_to_packet") is True,
            "exact packet patch-application proof missing")
    require(checks.get("source_receipt", {}).get("entries") == 10,
            "source receipt cardinality drift")
    require(checks.get("source_receipt", {}).get("status") == "MATCH_V3_MANIFEST_OVERLAY",
            "source receipt no longer matches manifest")

    required_patch_fragments = (
        "class V3BuildError(RuntimeError):",
        "def _require(condition, message):",
        "def _canonical_member_name(member):",
        "def canonical_archive_files(data, base):",
        "canonical = canonical_archive_files(data, m[\"base\"])",
        "len(data) == int(base.get(\"bytes\", -1))",
        "len(files) == int(base.get(\"files\", -1))",
        "member_count <= MAX_CANONICAL_MEMBERS",
        "total <= MAX_CANONICAL_TOTAL_BYTES",
        "member.size <= MAX_CANONICAL_FILE_BYTES",
        "not getattr(member, \"issparse\", lambda: False)()",
        "duplicate normalized member",
        "special member is not allowed",
        "regular file shadows another member",
        "len(first) >= 2 and first[0].isalpha() and first[1] == \":\"",
        "for name in (\"apply_v3.py\", \"build_v3.py\"):",
        "source_checks/test_build_v3_closure.py",
        "(\"C:drive.py\", \"drive prefix\")",
        "test_parent_escape_is_rejected_before_filesystem_write",
    )
    for fragment in required_patch_fragments:
        require(fragment in patch, "required patch fragment missing: %s" % fragment)
    require(patch.count("def canonical_archive_files(data, base):") == 1,
            "canonical archive decoder cardinality drift")
    require(patch.count("source_checks/test_build_v3_closure.py") >= 2,
            "source contract is not receipt-bound and added")

    receipt_lines = [line for line in SOURCE_RECEIPT.read_text(encoding="utf-8").splitlines()
                     if line.strip()]
    require(receipt_lines[0] == "SOURCE_RECEIPT_OK 10", "source receipt header drift")
    entries = {}
    for line in receipt_lines[1:]:
        name, digest = line.split(" ", 1)
        require(name not in entries, "duplicate source receipt key: %s" % name)
        require(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
                "invalid source receipt digest: %s" % name)
        entries[name] = digest
    require(len(entries) == 10, "source receipt does not contain ten unique entries")
    require(entries.get("build_v3.py") == EXPECTED_BUILDER,
            "executed builder is not bound in source receipt")
    require(entries.get("source_checks/test_build_v3_closure.py") == EXPECTED_TEST,
            "source contract is not bound in source receipt")

    print("SOL_BOUNDARY_EVIDENCE_OK")
    print("patch_sha256=" + EXPECTED_PATCH)
    print("packet_sha256=" + EXPECTED_PACKET)
    print("source_receipt_entries=10")
    print("local_contracts=8_normal+8_optimized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
