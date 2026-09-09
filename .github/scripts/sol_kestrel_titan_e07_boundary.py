#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Apply, verify, package, and publish the bounded TITAN E07 source repair."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
LAB = ROOT / "revenue/kaggriculture/cloud-execution-lab"
SOURCE = LAB / "frozen_selected.py"
TESTS = LAB / "test_e07_same_turn_funding.py"
RECEIPT = ROOT / "p/sol-kestrel-titan-e07-source-boundary-repair-20260909-01.md"
BRANCH = os.environ["GITHUB_REF_NAME"]

OLD_SCAN = "    for source in range(target+1,len(original)):\n"
NEW_SCAN = (
    "    source_limit=barrier if barrier is not None else len(original)\n"
    "    for source in range(target+1,source_limit):\n"
)
TEST_MARKER = "    def test_sell_after_buy_product_boundary_cannot_move_into_prefix(self):"
TEST_INSERTION = '''    def test_sell_after_buy_product_boundary_cannot_move_into_prefix(self):
        obs,base=fixture(shed={'MILK':1},money=0)
        base['market']=[[],['BUY_SEED','CARROT',1],
                        ['BUY_PRODUCT','WHEAT',1],['SELL','MILK',1]]
        original=deepcopy(base['market'])
        out,info=fund(obs,base,{'MILK'})
        self.assertEqual(out,original)
        self.assertEqual(info['reason'],'no-safe-prefix-sale')
        self.assertEqual(info['target_index'],1)
        self.assertEqual(sale_quantities(out),sale_quantities(original))
        self.assertEqual(base['market'],original)

    def test_sell_before_buy_product_boundary_can_still_fund_fixed_buy(self):
        obs,base=fixture(shed={'MILK':2},money=0)
        base['market']=[[],['BUY_SEED','CARROT',1],
                        ['SELL','MILK',2],['BUY_PRODUCT','WHEAT',1]]
        original=deepcopy(base['market'])
        out,info=fund(obs,base,{'MILK'})
        self.assertTrue(info['applied'])
        self.assertEqual((info['target_index'],info['source_index']),(1,2))
        self.assertEqual(out[0],['SELL','MILK',1])
        self.assertEqual(out[1],original[1])
        self.assertEqual(out[2],['SELL','MILK',1])
        self.assertEqual(out[3],original[3])
        self.assertEqual(sale_quantities(out),sale_quantities(original))
        self.assertEqual(base['market'],original)

'''
TEST_SENTINEL = "\n\nclass CanonicalSameTurnFundingBinding(unittest.TestCase):"


def run(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def output(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def digest(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def apply_patch() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    tests_text = TESTS.read_text(encoding="utf-8")
    if NEW_SCAN in source_text and TEST_MARKER in tests_text and RECEIPT.exists():
        print("Exact repair already published on this branch; no-op second push.")
        raise SystemExit(0)
    if NEW_SCAN not in source_text:
        count = source_text.count(OLD_SCAN)
        if count != 1:
            raise RuntimeError(f"expected one vulnerable source scan; found {count}")
        SOURCE.write_text(source_text.replace(OLD_SCAN, NEW_SCAN, 1), encoding="utf-8")
    if TEST_MARKER not in tests_text:
        count = tests_text.count(TEST_SENTINEL)
        if count != 1:
            raise RuntimeError(f"canonical test insertion point count is {count}")
        TESTS.write_text(
            tests_text.replace(
                TEST_SENTINEL,
                "\n\n" + TEST_INSERTION + "class CanonicalSameTurnFundingBinding(unittest.TestCase):",
                1,
            ),
            encoding="utf-8",
        )


def verify_and_build() -> tuple[str, dict[str, object]]:
    runtime = json.loads(
        (LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json").read_text(encoding="utf-8")
    )
    old_sha = str(runtime["sha256"])
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(ROOT / "revenue/kaggriculture/cloud-runtime-pulse"),
            str(ROOT / "revenue/kaggriculture/cloud-quickstep"),
            str(LAB),
        ]
    )
    run(sys.executable, "-B", "-m", "py_compile", "frozen_selected.py", "test_e07_same_turn_funding.py", cwd=LAB, env=env)
    run(
        sys.executable,
        "-B",
        "-m",
        "unittest",
        "-v",
        "test_e07_hosted_source_path",
        "test_e07_same_turn_funding",
        "test_joint_market_slots",
        "test_e10_floor_cycle",
        cwd=LAB,
        env=env,
    )
    run(sys.executable, "-B", "build_integrated.py", cwd=LAB, env=env)
    run(sys.executable, "-B", "build_integrated.py", "--check", cwd=LAB, env=env)
    run(
        sys.executable,
        "-B",
        "-m",
        "unittest",
        "-v",
        "test_release_consistency",
        "test_build_publication",
        cwd=LAB,
        env=env,
    )
    new_receipt = json.loads(
        (LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json").read_text(encoding="utf-8")
    )
    return old_sha, new_receipt


def write_receipt(old_sha: str, new_receipt: dict[str, object]) -> Path:
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "unknown")
    checkout = output("git", "rev-parse", "HEAD")
    RECEIPT.write_text(
        f"""# SOL-KESTREL — TITAN E07 BUY_PRODUCT source-boundary repair

Operation: `TITAN-E07-BUY-PRODUCT-SOURCE-BOUNDARY-REPAIR-20260909-02`
Workflow run: `{run_id}` attempt `{attempt}`
Cloud checkout before publication: `{checkout}`

## Repair

`fund_same_turn_acquisition` now limits candidate SELL sources to the half-open interval after the failing fixed acquisition and before the first later `BUY_PRODUCT` hard boundary. A variable-price purchase therefore cannot be crossed while a safe pre-boundary SELL remains eligible.

## Discriminating contracts

- target index 1, `BUY_PRODUCT` barrier index 2, SELL source index 3: unchanged queue, `no-safe-prefix-sale`, exact sale quantities preserved;
- target index 1, SELL source index 2, `BUY_PRODUCT` barrier index 3: the safe sale still funds the fixed acquisition without moving either purchase.

## Verification actually run

- Python compilation for the source and focused test;
- `test_e07_hosted_source_path`;
- `test_e07_same_turn_funding`;
- `test_joint_market_slots`;
- `test_e10_floor_cycle`;
- deterministic `build_integrated.py` and `build_integrated.py --check`;
- `test_release_consistency`;
- `test_build_publication`.

## Release identities

- previous current archive preserved as `exports/historical/titan-{old_sha}.tar.gz`;
- new current archive: `{new_receipt['sha256']}` / `{new_receipt['bytes']}` bytes / `{new_receipt['runtime_files']}` runtime files;
- current source manifest: `{new_receipt['source_manifest_sha256']}`.

No official games, Kaggle/provider action, submission, rank, or playing-strength claim was made. This is a fail-closed market-order correctness repair.
""",
        encoding="utf-8",
    )
    return LAB / "exports/historical" / f"titan-{old_sha}.tar.gz"


def validate_surface(old_sha: str, historical: Path) -> list[str]:
    archive = LAB / "exports/titan-current.tar.gz"
    source_manifest = LAB / "runtime/integrated-selected/CURRENT-SOURCE.json"
    archive_receipt = LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
    changed = set(output("git", "diff", "--name-only").splitlines())
    allowed = {
        str(SOURCE.relative_to(ROOT)),
        str(TESTS.relative_to(ROOT)),
        str(archive.relative_to(ROOT)),
        str(source_manifest.relative_to(ROOT)),
        str(archive_receipt.relative_to(ROOT)),
        str(historical.relative_to(ROOT)),
        str(RECEIPT.relative_to(ROOT)),
    }
    unexpected = sorted(changed - allowed)
    required = allowed - {str(historical.relative_to(ROOT))}
    missing = sorted(required - changed)
    if unexpected:
        raise RuntimeError(f"unexpected changed paths: {unexpected}")
    if missing:
        raise RuntimeError(f"expected changed paths missing: {missing}")
    if not historical.exists():
        raise RuntimeError(f"historical archive not preserved: {historical}")
    historical_bytes, historical_sha = digest(historical)
    if historical_sha != old_sha:
        raise RuntimeError(
            f"historical archive mismatch: expected {old_sha}, got {historical_sha} ({historical_bytes} bytes)"
        )
    new_bytes, new_sha = digest(archive)
    print(
        json.dumps(
            {
                "changed_paths": sorted(changed),
                "new_archive": {"bytes": new_bytes, "sha256": new_sha},
                "historical_archive": {"bytes": historical_bytes, "sha256": historical_sha},
            },
            indent=2,
        )
    )
    return sorted(changed)


def publish(changed: list[str]) -> None:
    run("git", "config", "user.name", "SOL-KESTREL")
    run("git", "config", "user.email", "brycembusiness2@gmail.com")
    run("git", "add", "--", *changed)
    run("git", "diff", "--cached", "--check")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        raise RuntimeError("repair produced no staged change")
    run("git", "commit", "-m", "fix(titan): stop E07 funding at BUY_PRODUCT boundary")
    run("git", "push", "origin", f"HEAD:{BRANCH}")


def main() -> None:
    apply_patch()
    old_sha, new_receipt = verify_and_build()
    historical = write_receipt(old_sha, new_receipt)
    changed = validate_surface(old_sha, historical)
    publish(changed)


if __name__ == "__main__":
    main()
