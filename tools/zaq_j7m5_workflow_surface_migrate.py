#!/usr/bin/env python3
"""Fresh-main exact-byte recovery for Commons workflow surface issue #14644.

Recovery lineage:
- original issue/source owner: Z-SOL-LOOM
- stale recovery design: Z-OrbitLoom-2025-Q6R4 (ZOL-Q6R4)
- fresh-main recovery/finalization: Z-AuroraQuarry-0821-J7M5 (ZAQ-J7M5)

Archives every active workflow outside the historical retained set and structural
auditor, preserving exact bytes and inventory digests, restores the drifted
commercial-deal-room recipe from its archive-origin trust anchor, then removes
this temporary recovery scaffolding before validation/commit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ci/workflow-surface.json"
WORKFLOW_DIR = ROOT / ".github/workflows"
SELF_SCRIPT = ROOT / "tools/zaq_j7m5_workflow_surface_migrate.py"
SELF_WORKFLOW = ROOT / ".github/workflows/zaq-j7m5-workflow-surface-migrate.yml"
STRUCTURAL = ".github/workflows/workflow-surface.yml"
BASE_COMMIT = "3a02f826e634a5f43d752d54b033e313397116f1"
COMMERCIAL_ARCHIVE_ORIGIN_COMMIT = "b7fce9e369a279392931e3b43e291a39461cef52"


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

    commercial_source = ".github/workflows/commercial-deal-room.yml"
    commercial_row = existing_by_source[commercial_source]
    archive_path = commercial_row["archive"]
    historical = subprocess.check_output([
        "git", "show", f"{COMMERCIAL_ARCHIVE_ORIGIN_COMMIT}:{archive_path}"
    ], cwd=ROOT)
    if len(historical) != commercial_row["bytes"] or sha256(historical) != commercial_row["sha256"]:
        raise SystemExit("archive-origin commercial-deal-room bytes do not match inventory trust anchor")
    (ROOT / archive_path).write_bytes(historical)

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
        "restored_historical_recipe": archive_path,
        "archived_sources": extra,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
