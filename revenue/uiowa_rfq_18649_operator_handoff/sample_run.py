#!/usr/bin/env python3
"""Run the UIOWA-100 synthetic operator sample without shell execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from preflight import DEFAULT_MANIFEST, load_manifest, repo_root_from, validate

HERE = Path(__file__).resolve().parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_command(command: list[str], out_dir: Path) -> list[str]:
    return [arg.replace("${OUT}", str(out_dir)) for arg in command]


def inventory_outputs(out_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not out_dir.exists():
        return results
    for path in sorted(p for p in out_dir.rglob("*") if p.is_file()):
        results.append(
            {
                "path": str(path.relative_to(out_dir)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return results


def run_sample(
    manifest: dict[str, Any],
    root: Path,
    out_dir: Path,
    timeout: float,
    dry_run: bool,
    selected_assets: set[str] | None = None,
) -> dict[str, Any]:
    preflight = validate(manifest, root)
    if not preflight["ok"]:
        raise RuntimeError("preflight failed: " + "; ".join(preflight["errors"]))

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    steps: list[dict[str, Any]] = []
    for asset in manifest["assets"]:
        commands = asset.get("sample_commands") or []
        if not commands:
            continue
        if selected_assets and asset["asset_id"] not in selected_assets:
            continue

        workdir = (root / asset["working_dir"]).resolve()
        for index, command in enumerate(commands):
            resolved = resolve_command(command, out_dir)
            argv = [sys.executable, *resolved]
            step: dict[str, Any] = {
                "asset_id": asset["asset_id"],
                "work_order": asset["work_order"],
                "command_index": index,
                "cwd": str(workdir.relative_to(root)),
                "argv": [sys.executable, *resolved],
                "dry_run": dry_run,
            }
            if dry_run:
                step.update({"returncode": None, "elapsed_seconds": 0.0})
                steps.append(step)
                continue

            started = time.perf_counter()
            completed = subprocess.run(
                argv,
                cwd=workdir,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            elapsed = time.perf_counter() - started
            step.update(
                {
                    "returncode": completed.returncode,
                    "elapsed_seconds": round(elapsed, 6),
                    "stdout_sha256": sha256_bytes(completed.stdout),
                    "stderr_sha256": sha256_bytes(completed.stderr),
                    "stdout_excerpt": completed.stdout.decode("utf-8", errors="replace")[-4000:],
                    "stderr_excerpt": completed.stderr.decode("utf-8", errors="replace")[-4000:],
                }
            )
            steps.append(step)
            if completed.returncode != 0:
                break
        if steps and steps[-1].get("returncode") not in (None, 0):
            break

    receipt: dict[str, Any] = {
        "schema": "uiowa.operator-sample-run.v1",
        "snapshot_main_sha": manifest["snapshot_main_sha"],
        "dry_run": dry_run,
        "selected_assets": sorted(selected_assets) if selected_assets else "all_executable_assets",
        "steps": steps,
        "outputs": inventory_outputs(out_dir),
        "success": all(step.get("returncode") in (None, 0) for step in steps),
        "guardrails": [
            "No shell=True execution is used.",
            "Commands come only from the checked-in operator manifest.",
            "The checked-in sample inputs are synthetic preparation artifacts.",
            "No network endpoint, credential, schedule, bid submission, or University system is invoked by this runner.",
        ],
    }
    receipt_path = out_dir / "sample-run-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--asset",
        action="append",
        dest="assets",
        help="Run only a named executable asset; repeat to select multiple.",
    )
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be > 0")
    manifest = load_manifest(args.manifest)
    root = (args.root or repo_root_from()).resolve()
    known = {asset["asset_id"] for asset in manifest.get("assets", [])}
    selected = set(args.assets or [])
    unknown = selected - known
    if unknown:
        parser.error(f"unknown --asset values: {sorted(unknown)}")

    receipt = run_sample(
        manifest,
        root,
        args.out,
        args.timeout,
        args.dry_run,
        selected or None,
    )
    print(
        f"UIOWA-100 sample: {'PASS' if receipt['success'] else 'FAIL'} "
        f"steps={len(receipt['steps'])} outputs={len(receipt['outputs'])} "
        f"dry_run={receipt['dry_run']}"
    )
    print(receipt["receipt_path"])
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
