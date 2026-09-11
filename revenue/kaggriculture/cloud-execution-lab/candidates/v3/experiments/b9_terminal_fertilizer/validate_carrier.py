#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import statistics
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
EXPECTED_SEEDS = tuple(range(2611151001, 2611151009))
EXPECTED_CELLS = frozenset((seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1))
PREDECESSOR_FACTOR_SHA256 = "e8d9a3c0e933557e03e214e8f3edb447a9e6338364d2014cded87cfe52d63f5d"
CURRENT_FACTOR_GIT_BLOB = "fb0caef5a6d2896f62a92e6f1c52b719832b5ba5"
EXPECTED_PROVENANCE = {
    "engine_ref": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
    "packaged_git_commit": "d5eca97c25dff2e51bbf8ccd832caf7198beaff7",
    "outer_sha256": "43bde326c4762072593ee6e461ee4bcfb21b9556bd3addb109a6a76fa0af4a99",
    "inner_archive_sha256": "65bcc97236dd4fda8617f3b5c6e3a7aa353ba00165a75886ed36741d2531d81e",
    "wrapper_sha256": "c71b1dc3fbe65a893114e5155a05cdfc9efc5e9b67b245b1d01ea8f9fcaf1950",
    "source_sha256": {
        "arlene.py": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
        "baseline.py": "7868af58026368d135559806d49595ac5456fba083454f2b65674c2b81224f95",
        "candidate.py": "f836b4a2dc209c01eeaaabef8240958554796e0cf9201aee78ad0014ecda4ad0",
        "main.py": "458868f600d96754f4e1ddd14a125f80b61da9603d175bdc1627d66fb5c2e6f7",
        "r04_full_router.py": "8246c408908a2cab76d6bbe4c7655a429987395a0b0a78b31acc87ba575fb90f",
    },
    "engine_sha256": {
        "kaggriculture.py": "431fa50b17b9d81b66fa01eb64121050786000dddfe8d52c16b9dcd313217163",
        "kaggriculture.json": "ee53c4fe86b5c07bf72c20e52f93930b983d1ac99e82a7cc607c1f4f50d71dbf",
        "utils.py": "130478025806d849d0b5da6296179bd2c5450e8dbb806bb9a2ba94435b5d0947",
    },
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


def finite_number(value, label):
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise AssertionError(f"{label}: finite JSON number required, got {value!r}")
    return float(value)


def exact_pair(value, label):
    if not isinstance(value, list) or len(value) != 2:
        raise AssertionError(f"{label}: exact two-score vector required")
    return (
        finite_number(value[0], f"{label}[0]"),
        finite_number(value[1], f"{label}[1]"),
    )


def recompute_panel(name, panel):
    if not isinstance(panel, dict):
        raise AssertionError(f"{name}: panel must be object")
    rows = panel.get("rows")
    if not isinstance(rows, list):
        raise AssertionError(f"{name}: rows must be list")
    indexed = {}
    margins = []
    owns = []
    rivals = []
    expected_row_keys = {
        "seed", "candidate_seat", "control_scores", "arm_scores",
        "delta_own", "delta_rival", "delta_margin",
    }
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != expected_row_keys:
            raise AssertionError(f"{name}[{index}]: exact row schema required")
        seed = row["seed"]
        seat = row["candidate_seat"]
        if type(seed) is not int or seed not in EXPECTED_SEEDS:
            raise AssertionError(f"{name}[{index}]: invalid seed {seed!r}")
        if type(seat) is not int or seat not in (0, 1):
            raise AssertionError(f"{name}[{index}]: invalid candidate_seat {seat!r}")
        key = (seed, seat)
        if key in indexed:
            raise AssertionError(f"{name}: duplicate paired cell {key!r}")
        indexed[key] = row

        control = exact_pair(row["control_scores"], f"{name}[{index}].control_scores")
        arm = exact_pair(row["arm_scores"], f"{name}[{index}].arm_scores")
        delta_own = arm[seat] - control[seat]
        delta_rival = arm[1 - seat] - control[1 - seat]
        delta_margin = delta_own - delta_rival
        stored_own = finite_number(row["delta_own"], f"{name}[{index}].delta_own")
        stored_rival = finite_number(row["delta_rival"], f"{name}[{index}].delta_rival")
        stored_margin = finite_number(row["delta_margin"], f"{name}[{index}].delta_margin")
        if (stored_own, stored_rival, stored_margin) != (delta_own, delta_rival, delta_margin):
            raise AssertionError(
                f"{name}[{index}]: stored delta mismatch "
                f"stored={(stored_own, stored_rival, stored_margin)!r} "
                f"recomputed={(delta_own, delta_rival, delta_margin)!r}"
            )
        owns.append(delta_own)
        rivals.append(delta_rival)
        margins.append(delta_margin)

    if frozenset(indexed) != EXPECTED_CELLS:
        missing = sorted(EXPECTED_CELLS - frozenset(indexed))
        extra = sorted(frozenset(indexed) - EXPECTED_CELLS)
        raise AssertionError(f"{name}: exact paired cell set mismatch missing={missing!r} extra={extra!r}")

    summary = {
        "max_delta_margin": max(margins),
        "mean_delta_margin": statistics.mean(margins),
        "mean_delta_own": statistics.mean(owns),
        "mean_delta_rival": statistics.mean(rivals),
        "median_delta_margin": statistics.median(margins),
        "min_delta_margin": min(margins),
        "n": len(margins),
        "negative": sum(value < 0 for value in margins),
        "positive": sum(value > 0 for value in margins),
        "zero": sum(value == 0 for value in margins),
    }
    if panel.get("summary") != summary:
        raise AssertionError(
            f"{name}: summary mismatch stored={panel.get('summary')!r} recomputed={summary!r}"
        )
    return summary


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
if run("git", "rev-parse", f"HEAD:{PREFIX}/terminal_fertilizer.py") != CURRENT_FACTOR_GIT_BLOB:
    raise AssertionError("current repaired factor Git blob drift")

receipt = json.loads((HERE / "B9-ECONOMICS-20260911.json").read_text())
if receipt.get("schema") != "titan-v31-b9-terminal-fertilizer/v1":
    raise AssertionError("receipt schema drift")
if receipt.get("status") != "evidence-only_default-off":
    raise AssertionError("receipt status drift")
if receipt.get("base_commit") != EXPECTED_BASE:
    raise AssertionError("receipt base commit drift")
if receipt.get("factor_sha256") != PREDECESSOR_FACTOR_SHA256:
    raise AssertionError("predecessor factor receipt SHA drift")
if receipt.get("collect_steps") != [716, 717] or receipt.get("terminal_step") != 718:
    raise AssertionError("receipt factor timing drift")
if receipt.get("package_provenance") != EXPECTED_PROVENANCE:
    raise AssertionError("evaluator/package/opponent/source provenance drift")

panels = receipt.get("panels")
if not isinstance(panels, dict) or set(panels) != {"frozen_arlene", "frozen_exact_v31"}:
    raise AssertionError("receipt panel set drift")
arlene = recompute_panel("frozen_arlene", panels["frozen_arlene"])
v31 = recompute_panel("frozen_exact_v31", panels["frozen_exact_v31"])
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
    raise AssertionError("recomputed Arlene economics drift")
if v31 != {
    "max_delta_margin": 0.0,
    "mean_delta_margin": 0.0,
    "mean_delta_own": 0.0,
    "mean_delta_rival": 0.0,
    "median_delta_margin": 0.0,
    "min_delta_margin": 0.0,
    "n": 16,
    "negative": 0,
    "positive": 0,
    "zero": 16,
}:
    raise AssertionError("recomputed V3.1 equivalence drift")

current_factor_sha256 = hashlib.sha256((HERE / "terminal_fertilizer.py").read_bytes()).hexdigest()
subprocess.run(
    [sys.executable, "-B", "-m", "unittest", "-v", "test_terminal_fertilizer.py"],
    cwd=HERE,
    check=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
)
if run("git", "status", "--porcelain"):
    raise AssertionError("validation dirtied checkout")
print(
    "B9 TERMINAL FERTILIZER CARRIER PASS "
    f"head={head} predecessor_factor_sha256={PREDECESSOR_FACTOR_SHA256} "
    f"current_factor_sha256={current_factor_sha256} current_factor_git_blob={CURRENT_FACTOR_GIT_BLOB}"
)
