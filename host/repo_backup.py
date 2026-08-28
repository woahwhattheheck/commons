#!/usr/bin/env python3
"""Create, verify, and restore full Git-bundle backups without closing the repo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "commons-open-repo-backup/v1"
DRILL_SCHEMA_VERSION = "commons-open-repo-backup-drill/v1"
ALLOWED_STORAGE = frozenset({"github-actions-artifact"})
ARTIFACT_RETENTION_DAYS = 90
DEFAULT_ARTIFACT_NAME = "commons-open-repo-backup"
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")

DRILL_FIELDS = frozenset(
    {
        "schema_version",
        "state",
        "created_at",
        "storage",
        "retention_days",
        "artifact_name",
        "github_outage_protection",
        "same_repo_copy",
        "owner_disk",
        "secrets_present",
        "independent_of_git_objects",
        "independent_of_owner_disk",
        "github_hosted",
        "head_sha",
        "bundle",
        "bundle_sha256",
        "ref_count",
        "restored_head_sha",
        "bare",
        "run_id",
        "run_attempt",
        "repository",
        "ref",
        "sha",
    }
)


class BackupError(RuntimeError):
    """A snapshot, manifest, or restore failed its measured contract."""


def _run(
    args: list[str],
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise BackupError(f"git {' '.join(args)} failed: {detail}")
    return completed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise BackupError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except OSError as error:
        raise BackupError(f"refusing to overwrite {path}: {error}") from error
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _bundle_heads(bundle: Path) -> list[dict[str, str]]:
    completed = _run(["bundle", "list-heads", str(bundle)])
    heads = []
    for line in completed.stdout.splitlines():
        sha, separator, ref = line.partition(" ")
        if not separator or not SHA_RE.fullmatch(sha) or not ref.strip():
            raise BackupError(f"invalid bundle head: {line!r}")
        heads.append({"ref": ref.strip(), "sha": sha})
    if not heads:
        raise BackupError("bundle has no refs")
    return sorted(heads, key=lambda row: row["ref"])


def _repo_heads(source: Path) -> list[dict[str, str]]:
    # `git bundle --all` records HEAD plus every ref. `for-each-ref` omits HEAD,
    # so compare against `show-ref --head` or the snapshot rejects a valid bundle.
    completed = _run(
        ["show-ref", "--head"],
        cwd=source,
    )
    heads = []
    for line in completed.stdout.splitlines():
        sha, separator, ref = line.partition(" ")
        if separator and SHA_RE.fullmatch(sha) and ref.strip():
            heads.append({"ref": ref.strip(), "sha": sha})
    return sorted(heads, key=lambda row: row["ref"])


def snapshot(source: Path, output_dir: Path) -> Path:
    source = source.resolve()
    output_dir = output_dir.resolve()
    if _run(["rev-parse", "--is-inside-work-tree"], cwd=source).stdout.strip() != "true":
        raise BackupError(f"not a Git work tree: {source}")
    head_sha = _run(["rev-parse", "HEAD"], cwd=source).stdout.strip()
    if not SHA_RE.fullmatch(head_sha):
        raise BackupError("HEAD is not a full object id")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle = output_dir / f"commons-{stamp}-{head_sha[:12]}.bundle"
    if bundle.exists():
        raise BackupError(f"refusing to overwrite snapshot: {bundle}")
    _run(["bundle", "create", str(bundle), "--all"], cwd=source)
    bundle_heads = _bundle_heads(bundle)
    repo_heads = _repo_heads(source)
    if bundle_heads != repo_heads:
        bundle.unlink(missing_ok=True)
        raise BackupError("bundle ref inventory differs from source")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "head_sha": head_sha,
        "bundle": bundle.name,
        "bundle_sha256": _sha256(bundle),
        "refs": bundle_heads,
        "source": str(source),
    }
    manifest_path = bundle.with_suffix(".manifest.json")
    _write_exclusive_json(manifest_path, manifest)
    return manifest_path


def read_manifest(manifest_path: Path) -> tuple[dict[str, Any], Path]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BackupError(f"manifest unreadable: {manifest_path}: {error}") from error
    required = {
        "schema_version",
        "created_at",
        "head_sha",
        "bundle",
        "bundle_sha256",
        "refs",
        "source",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise BackupError("manifest fields drifted")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise BackupError("manifest schema version drifted")
    if not SHA_RE.fullmatch(str(manifest["head_sha"])):
        raise BackupError("manifest HEAD is invalid")
    bundle_name = str(manifest["bundle"])
    if Path(bundle_name).name != bundle_name:
        raise BackupError("manifest bundle must be a sibling filename")
    bundle = manifest_path.resolve().parent / bundle_name
    if not bundle.is_file():
        raise BackupError(f"bundle missing: {bundle}")
    return manifest, bundle


def verify(manifest_path: Path) -> dict[str, Any]:
    manifest, bundle = read_manifest(manifest_path)
    actual_sha = _sha256(bundle)
    if actual_sha != manifest["bundle_sha256"]:
        raise BackupError("bundle sha256 mismatch")
    actual_refs = _bundle_heads(bundle)
    if actual_refs != manifest["refs"]:
        raise BackupError("bundle refs differ from manifest")
    if not any(row["sha"] == manifest["head_sha"] for row in actual_refs):
        raise BackupError("manifest HEAD is absent from bundle refs")
    return {
        "state": "VERIFIED",
        "manifest": str(manifest_path),
        "bundle": str(bundle),
        "bundle_sha256": actual_sha,
        "head_sha": manifest["head_sha"],
        "refs": len(actual_refs),
    }


def restore(manifest_path: Path, target: Path, bare: bool = False) -> dict[str, Any]:
    receipt = verify(manifest_path)
    target = target.resolve()
    if target.exists():
        raise BackupError(f"refusing to overwrite restore target: {target}")
    clone_args = ["clone"]
    if bare:
        clone_args.append("--bare")
    clone_args.extend([receipt["bundle"], str(target)])
    _run(clone_args)
    restored_head = _run(["rev-parse", "HEAD"], cwd=target).stdout.strip()
    if restored_head != receipt["head_sha"]:
        raise BackupError(
            f"restored HEAD {restored_head} != manifest {receipt['head_sha']}"
        )
    receipt.update(
        {
            "state": "RESTORED",
            "target": str(target),
            "restored_head_sha": restored_head,
            "bare": bare,
        }
    )
    return receipt


def github_run_fields() -> dict[str, str]:
    return {
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "ref": os.environ.get("GITHUB_REF", ""),
        "sha": os.environ.get("GITHUB_SHA", ""),
    }


def make_drill_receipt(
    *,
    storage: str,
    retention_days: int,
    artifact_name: str,
    restore_receipt: dict[str, Any],
    run: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the exclusive CI drill receipt.

    Forced flags cannot be overridden: github_outage_protection, same_repo_copy,
    owner_disk, and secrets_present are always False. Storage must be the
    measured GitHub Actions artifact store. This function will not mint S3,
    GCS, Drive, or Oracle receipts.
    """
    if storage not in ALLOWED_STORAGE:
        raise BackupError(
            f"storage {storage!r} is not a measured independent store; "
            "do not mint an unmeasured provider receipt"
        )
    if retention_days != ARTIFACT_RETENTION_DAYS:
        raise BackupError(
            f"retention_days must be {ARTIFACT_RETENTION_DAYS} for github-actions-artifact"
        )
    if not artifact_name or Path(artifact_name).name != artifact_name:
        raise BackupError("artifact name must be a bare filename")
    if restore_receipt.get("state") != "RESTORED":
        raise BackupError("drill receipt requires a RESTORED readback")
    required_restore = ("head_sha", "bundle", "bundle_sha256", "refs", "restored_head_sha")
    missing = [key for key in required_restore if key not in restore_receipt]
    if missing:
        raise BackupError(f"restore receipt missing {missing}")
    if restore_receipt["restored_head_sha"] != restore_receipt["head_sha"]:
        raise BackupError("restore readback HEAD does not match manifest")
    run = github_run_fields() if run is None else run
    receipt = {
        "schema_version": DRILL_SCHEMA_VERSION,
        "state": "DRILLED",
        "created_at": _utc_now(),
        "storage": "github-actions-artifact",
        "retention_days": ARTIFACT_RETENTION_DAYS,
        "artifact_name": artifact_name,
        "github_outage_protection": False,
        "same_repo_copy": False,
        "owner_disk": False,
        "secrets_present": False,
        "independent_of_git_objects": True,
        "independent_of_owner_disk": True,
        "github_hosted": True,
        "head_sha": restore_receipt["head_sha"],
        "bundle": Path(str(restore_receipt["bundle"])).name,
        "bundle_sha256": restore_receipt["bundle_sha256"],
        "ref_count": restore_receipt["refs"],
        "restored_head_sha": restore_receipt["restored_head_sha"],
        "bare": bool(restore_receipt.get("bare")),
        "run_id": str(run.get("run_id", "")),
        "run_attempt": str(run.get("run_attempt", "")),
        "repository": str(run.get("repository", "")),
        "ref": str(run.get("ref", "")),
        "sha": str(run.get("sha", "")),
    }
    # Re-force so a mutated restore_receipt or run dict cannot mint a false claim.
    receipt["github_outage_protection"] = False
    receipt["same_repo_copy"] = False
    receipt["owner_disk"] = False
    receipt["secrets_present"] = False
    receipt["storage"] = "github-actions-artifact"
    receipt["retention_days"] = ARTIFACT_RETENTION_DAYS
    if set(receipt) != DRILL_FIELDS:
        raise BackupError("drill receipt fields drifted")
    return receipt


def drill(
    source: Path,
    output_dir: Path,
    restore_dir: Path,
    *,
    storage: str,
    retention_days: int,
    artifact_name: str = DEFAULT_ARTIFACT_NAME,
    bare: bool = True,
    run: dict[str, str] | None = None,
) -> dict[str, Any]:
    manifest_path = snapshot(source, output_dir)
    restored = restore(manifest_path, restore_dir, bare=bare)
    receipt = make_drill_receipt(
        storage=storage,
        retention_days=retention_days,
        artifact_name=artifact_name,
        restore_receipt=restored,
        run=run,
    )
    receipt_path = output_dir.resolve() / "drill-receipt.json"
    _write_exclusive_json(receipt_path, receipt)
    return {
        **receipt,
        "manifest": str(manifest_path),
        "receipt": str(receipt_path),
        "target": restored["target"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("snapshot")
    make.add_argument("--source", type=Path, default=Path.cwd())
    make.add_argument("--output-dir", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("manifest", type=Path)
    recover = commands.add_parser("restore")
    recover.add_argument("manifest", type=Path)
    recover.add_argument("target", type=Path)
    recover.add_argument("--bare", action="store_true")
    exercise = commands.add_parser("drill")
    exercise.add_argument("--source", type=Path, default=Path.cwd())
    exercise.add_argument("--output-dir", type=Path, required=True)
    exercise.add_argument("--restore-dir", type=Path, required=True)
    exercise.add_argument("--bare", action="store_true")
    exercise.add_argument("--storage", required=True)
    exercise.add_argument("--retention-days", type=int, required=True)
    exercise.add_argument("--artifact-name", default=DEFAULT_ARTIFACT_NAME)
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            output = {"state": "SNAPSHOT", "manifest": str(snapshot(args.source, args.output_dir))}
        elif args.command == "verify":
            output = verify(args.manifest)
        elif args.command == "drill":
            output = drill(
                args.source,
                args.output_dir,
                args.restore_dir,
                storage=args.storage,
                retention_days=args.retention_days,
                artifact_name=args.artifact_name,
                bare=args.bare,
            )
        else:
            output = restore(args.manifest, args.target, args.bare)
        print(json.dumps(output, sort_keys=True))
        return 0
    except BackupError as error:
        print(f"BACKUP_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
