#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Adapt the independently reviewed B11 a612 screen onto shipped 8e3+B5+JIT.

This file deliberately does not copy the 351-line predecessor gate.  It retrieves
that exact Git object, verifies its blob identity, applies a small fail-closed
source transform, and executes the result.  The transform changes only current-root
custody/labels, native evaluator metadata validation, and the two shipped B5 flags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

DONOR_RUNNER_COMMIT = "8fb616f5b9a7c04506547414fd3aa13e9c8afe9b"
DONOR_RUNNER_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/"
    "experiments/b11_a612_screen/run_current_stack.py"
)
DONOR_RUNNER_BLOB = "c1cfe67b91121fc8de2843cf11ca17ed2be8e716"
OLD_ROOT = "a6120d0ea1bdb75eb0da2239220efce551f624a6"
ROOT = "8e3d92a286806f9f9525973ee7d359b629a11487"
OLD_PACKAGE = "400ae640f3258b6a6ff19f9da99c66ef9c433e315febb1d72c75296cddeb277c"
ROOT_PACKAGE = "4d920b2d8948488dc4f491a3a2b3d038c830d723baaaaba1e4470799b66f7d13"
BASE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
HISTORICAL_REL = (
    'LAB_REL / "exports" / "historical" / '
    '"titan-5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1.tar.gz"'
)
EXPECTED_B11_BLOB = "94b270f36c4a27b3d958ac3420bbe5764ac327a1"


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1)


def transform(source: str) -> str:
    source = replace_once(source, OLD_ROOT, ROOT, "root")
    source = replace_once(source, OLD_PACKAGE, ROOT_PACKAGE, "package digest")
    source = replace_once(
        source,
        'CANONICAL_REL = LAB_REL / "exports" / "titan-current.tar.gz"',
        f"CANONICAL_REL = {HISTORICAL_REL}",
        "immutable base path",
    )
    source = replace_once(
        source,
        '        "r04_strawberry_topup": True,\n'
        '    }\n',
        '        "r04_strawberry_topup": True,\n'
        '        "r04_b5_carrot_fertilizer": True,\n'
        '        "r04_b5_jit_fertilize": True,\n'
        '    }\n',
        "score-facing B5 config custody",
    )
    source = replace_once(
        source,
        "    strawberry_topup=True,\n"
        ")\n",
        "    strawberry_topup=True,\n"
        "    b5_carrot_fertilizer=True,\n"
        "    b5_jit_fertilize=True,\n"
        ")\n",
        "B5 install args",
    )
    source = replace_once(
        source,
        '    if opponents != list(OPPONENTS):\n'
        '        raise AssertionError(f"{label}: opponent metadata drift {opponents!r}")\n',
        """    if report.get('schema_version') != 1:
        raise AssertionError(f"{label}: evaluator schema drift {report.get('schema_version')!r}")
    if report.get('agent_rng_seed') != 20260911:
        raise AssertionError(f"{label}: RNG metadata drift {report.get('agent_rng_seed')!r}")
    if not isinstance(opponents, dict) or set(opponents) != set(OPPONENTS):
        raise AssertionError(f"{label}: opponent metadata drift {opponents!r}")
    expected_entries = {"8e3_self": "main.py", "arlene": "arlene.py"}
    for name, entry in expected_entries.items():
        fp = opponents.get(name)
        if (not isinstance(fp, dict) or fp.get("entry") != entry
                or fp.get("callable") != "agent"
                or not isinstance(fp.get("sha256"), str) or len(fp["sha256"]) != 64):
            raise AssertionError(f"{label}: opponent fingerprint drift {name}: {fp!r}")
    candidate_fp = report.get("candidate")
    expected_candidate = "main.py" if label == "control" else "b11_candidate.py"
    if (not isinstance(candidate_fp, dict) or candidate_fp.get("entry") != expected_candidate
            or candidate_fp.get("callable") != "agent"
            or not isinstance(candidate_fp.get("sha256"), str) or len(candidate_fp["sha256"]) != 64):
        raise AssertionError(f"{label}: candidate fingerprint drift {candidate_fp!r}")
""",
        "native evaluator fingerprint map",
    )

    # All remaining a612 tokens are labels / schema names / temp prefixes / self labels.
    source = source.replace("a612", "8e3").replace("A612", "8E3")
    if "a612" in source or "A612" in source:
        raise AssertionError("stale a612 label survived transform")

    compile(source, "<b11-8e3-transformed>", "exec")
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    donor = git(repo, "show", f"{DONOR_RUNNER_COMMIT}:{DONOR_RUNNER_PATH}")
    actual = git_blob_sha(donor)
    if actual != DONOR_RUNNER_BLOB:
        raise AssertionError(f"reviewed B11 runner blob drift: {actual}")
    source = transform(donor.decode("utf-8"))

    with tempfile.TemporaryDirectory(prefix="titan-v31-8e3-b11-runner-") as tmp:
        adapted = Path(tmp) / "run_current_stack_8e3.py"
        adapted.write_text(source, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(adapted),
                "--repo-root",
                str(repo),
                "--output-dir",
                str(output),
            ],
            cwd=repo,
            check=True,
        )

    receipt_path = output / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "titan-v31-b11-8e3-screen/v1":
        raise AssertionError(f"adapted receipt schema drift: {receipt.get('schema')!r}")
    if receipt.get("canonical_head") != ROOT:
        raise AssertionError(f"adapted root drift: {receipt.get('canonical_head')!r}")
    donor_meta = receipt.get("reviewed_b11_donor")
    if not isinstance(donor_meta, dict) or donor_meta.get("blob") != EXPECTED_B11_BLOB:
        raise AssertionError(f"B11 source donor drift: {donor_meta!r}")

    receipt["current_root_adapter"] = {
        "donor_runner_commit": DONOR_RUNNER_COMMIT,
        "donor_runner_blob": DONOR_RUNNER_BLOB,
        "root": ROOT,
        "package_sha256": ROOT_PACKAGE,
        "canonical_base_sha256": BASE_SHA256,
        "native_evaluator_opponents": "fingerprint-map",
        "b5_carrot_fertilizer": True,
        "b5_jit_fertilize": True,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output / "receipt.md").open("a", encoding="utf-8") as handle:
        handle.write(
            "\n\n### Current-root adapter custody\n\n"
            f"- donor runner blob: `{DONOR_RUNNER_BLOB}`\n"
            f"- root: `{ROOT}`\n"
            f"- package: `{ROOT_PACKAGE}`\n"
            "- evaluator opponents metadata: native fingerprint map\n"
            "- B5 CARROT + JIT install/config flags: `true`\n"
        )
    print("B11_8E3_DISPOSITION", receipt.get("disposition"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
