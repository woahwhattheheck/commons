#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in (HERE, *HERE.parents) if (p / ".git").exists())
EXPECTED_BASE = "508b342fc46fa91e3d7cdc3f0b7e44934a187c14"
PREFIX = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/experiments/b9_terminal_fertilizer"
EXPECTED_PATHS = {
    ".github/workflows/titan-v31-b9-terminal-fertilizer.yml",
    f"{PREFIX}/B9-ECONOMICS-20260911.json",
    f"{PREFIX}/README.md",
    f"{PREFIX}/terminal_fertilizer.py",
    f"{PREFIX}/test_terminal_fertilizer.py",
    f"{PREFIX}/validate_carrier.py",
}


def run(*args):
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


head = run("git", "rev-parse", "HEAD")
expected = os.environ.get("TITAN_EXPECTED_HEAD_SHA", "").strip()
if not expected or head != expected:
    raise AssertionError(f"wrong head expected={expected!r} observed={head!r}")
if run("git", "status", "--porcelain"):
    raise AssertionError("dirty checkout before validation")
if run("git", "merge-base", EXPECTED_BASE, head) != EXPECTED_BASE:
    raise AssertionError("wrong frozen ancestry")
changed = {
    x
    for x in run("git", "diff", "--name-only", f"{EXPECTED_BASE}...{head}").splitlines()
    if x
}
if changed != EXPECTED_PATHS:
    raise AssertionError(
        f"wrong scope missing={sorted(EXPECTED_PATHS - changed)} extra={sorted(changed - EXPECTED_PATHS)}"
    )

receipt = json.loads((HERE / "B9-ECONOMICS-20260911.json").read_text())
actual = hashlib.sha256((HERE / "terminal_fertilizer.py").read_bytes()).hexdigest()
if receipt.get("factor_sha256") != actual:
    raise AssertionError("factor SHA mismatch")

arlene = receipt["panels"]["frozen_arlene"]["summary"]
v31 = receipt["panels"]["frozen_exact_v31"]["summary"]
if arlene != {
    "max_delta_margin": 8.0,
    "mean_delta_margin": 4.75,
    "mean_delta_own": 4.5,
    "mean_delta_rival": -0.25,
    "median_delta_margin": 5.0,
    "min_delta_margin": 0.0,
    "n": 16,
    "negative": 0,
    "positive": 12,
    "zero": 4,
}:
    raise AssertionError("Arlene summary drift")
if not (
    v31["n"] == 16
    and v31["negative"] == v31["positive"] == 0
    and v31["zero"] == 16
    and v31["mean_delta_margin"] == v31["mean_delta_own"] == v31["mean_delta_rival"] == 0.0
):
    raise AssertionError("V3.1 equivalence summary drift")

subprocess.run(
    [sys.executable, "-m", "unittest", "-v", "test_terminal_fertilizer.py"],
    cwd=HERE,
    check=True,
)
print(f"B9 TERMINAL FERTILIZER CARRIER PASS head={head} factor_sha256={actual}")
