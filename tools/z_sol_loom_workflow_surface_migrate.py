#!/usr/bin/env python3
"""One-shot exact-byte migration for Commons workflow surface issue #14644.

Runs only on the dedicated recovery branch. It archives every active workflow
outside the original retained set and the structural auditor, pins each new
archive row to the exact branch-base commit, restores the one drifted historical
recipe from its original trust anchor, and removes itself plus its temporary
workflow before validation/commit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ci/workflow-surface.json"
WORKFLOW_DIR = ROOT / ".github/workflows"
RECIPE_DIR = ROOT / "ci/workflow-recipes"
SELF_SCRIPT = ROOT / "tools/z_sol_loom_workflow_surface_migrate.py"
SELF_WORKFLOW = ROOT / ".github/workflows/z-sol-loom-workflow-surface-migrate.yml"
STRUCTURAL = ".github/workflows/workflow-surface.yml"
BASE_COMMIT = "c35b159817de42e79e2c29b267d7d8122c2baa05"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    retained = set(manifest["retained"])
    if len(retained) != len(manifest["retained"]):
        raise SystemExit("duplicate retained workflow")
    if STRUCTURAL in retained:
        raise SystemExit("structural auditor unexpectedly part of historical retained set")

    existing_by_source = {row["source"]: row for row in manifest["archived"]}
    existing_by_archive = {row["archive"]: row for row in manifest["archived"]}
    if len(existing_by_source) != len(manifest["archived"]) or len(existing_by_archive) != len(manifest["archived"]):
        raise SystemExit("duplicate archive inventory before migration")

    # Restore the canonical historical recipe instead of blessing post-archive
    # mutation. The inventory itself is the trust root for length/digest.
    commercial_source = ".github/workflows/commercial-deal-room.yml"
    commercial_row = existing_by_source[commercial_source]
    historical = subprocess.check_output([
        "git", "show", f"{manifest['source_commit']}:{commercial_source}"
    ], cwd=ROOT)
    if len(historical) != commercial_row["bytes"] or sha256(historical) != commercial_row["sha256"]:
        raise SystemExit("historical commercial-deal-room bytes do not match inventory trust anchor")
    (ROOT / commercial_row["archive"]).write_bytes(historical)

    active = sorted(
        p for p in WORKFLOW_DIR.iterdir()
        if p.is_file() and p.suffix in {".yml", ".yaml"} and p != SELF_WORKFLOW
    )
    extra = []
    for path in active:
        source = path.relative_to(ROOT).as_posix()
        if source in retained or source == STRUCTURAL:
            continue
        if source in existing_by_source:
            raise SystemExit(f"previously archived workflow was reactivated: {source}")
        archive = f"ci/workflow-recipes/{path.name}"
        if archive in existing_by_archive or (ROOT / archive).exists():
            raise SystemExit(f"archive destination already exists without matching inventory: {archive}")
        raw = path.read_bytes()
        (ROOT / archive).write_bytes(raw)
        manifest["archived"].append({
            "source": source,
            "archive": archive,
            "sha256": sha256(raw),
            "bytes": len(raw),
            "source_commit": BASE_COMMIT,
        })
        path.unlink()
        extra.append(source)

    manifest["archived"].sort(key=lambda row: row["source"])
    manifest["source_workflows"] = len(manifest["retained"]) + len(manifest["archived"])
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # The branch-only scaffolding must not survive into the candidate surface.
    SELF_WORKFLOW.unlink(missing_ok=True)
    SELF_SCRIPT.unlink(missing_ok=True)

    final_active = sorted(
        p.relative_to(ROOT).as_posix()
        for p in WORKFLOW_DIR.iterdir()
        if p.is_file() and p.suffix in {".yml", ".yaml"}
    )
    expected_active = retained | {STRUCTURAL}
    if set(final_active) != expected_active:
        missing = sorted(expected_active - set(final_active))
        unexpected = sorted(set(final_active) - expected_active)
        raise SystemExit(f"active surface mismatch after migration; missing={missing} unexpected={unexpected}")
    if len(final_active) > manifest["max_active_workflows"]:
        raise SystemExit("migration did not restore active workflow budget")

    print(json.dumps({
        "status": "MIGRATED_NOT_COMMITTED",
        "base_commit": BASE_COMMIT,
        "archived_now": len(extra),
        "active_after": len(final_active),
        "archive_inventory_after": len(manifest["archived"]),
        "source_workflows_after": manifest["source_workflows"],
        "restored_historical_recipe": commercial_row["archive"],
        "archived_sources": extra,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
