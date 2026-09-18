#!/usr/bin/env python3
"""Deterministic advisory rationalizer for a GitHub repository estate."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.repo_estate_rationalizer.schema import *
from tools.repo_estate_rationalizer.schema import _canon_time, _plain, _time
_AUTHORITY_GENERATION: tuple[tuple[str, bool], ...] = (
    ("advisory_only", True),
    ("repository_visibility_mutation_authorized", False),
    ("repository_archive_mutation_authorized", False),
    ("repository_delete_authorized", False),
    ("branch_or_actions_mutation_authorized", False),
    ("billing_or_spend_mutation_authorized", False),
    ("publication_safety_certified", False),
)


def _decision(
    repo: dict[str, Any],
    ev: dict[str, Any] | None,
    *,
    _trusted_owner_refs: frozenset[str] = frozenset(),
    _trusted_archive_refs: frozenset[str] = frozenset(),
    _secret_clear: str = "CLEAR",
    _public_class: str = "PUBLIC_RELEASE_OK",
    _legal_public: str = "CLEAR_FOR_PUBLIC_RELEASE",
) -> dict[str, Any]:
    if repo["visibility"] == "public":
        return {"repository": repo["name"], "state": "PUBLIC_ALREADY", "reasons": ["ALREADY_PUBLIC"], "branch_sha": repo["default_branch_sha"]}
    if ev is None:
        return {"repository": repo["name"], "state": "HOLD", "reasons": ["MISSING_PUBLICATION_RETENTION_EVIDENCE"], "branch_sha": repo["default_branch_sha"]}
    reasons: list[str] = []
    sha = repo["default_branch_sha"]
    if sha is None:
        reasons.append("MISSING_CURRENT_BRANCH_SHA")
    elif ev["default_branch_sha"] != sha:
        reasons.append("BRANCH_GENERATION_DRIFT")

    # Keeping data private is the fail-closed direction and never needs a
    # caller-provided publication credential.
    if ev["intent"] == "keep_private":
        return {"repository": repo["name"], "state": "KEEP_PRIVATE" if not reasons else "HOLD", "reasons": reasons or ["CONSERVATIVE_KEEP_PRIVATE"], "branch_sha": sha}

    if not ev["owner_authorized"]:
        reasons.append("OWNER_AUTHORITY_NOT_PROVEN")
    elif ev["owner_authority_ref"] not in _trusted_owner_refs:
        reasons.append("OWNER_AUTHORITY_NOT_SOURCE_TRUSTED")
    if ev["secret_scan"]["result"] != _secret_clear or not ev["secret_scan"]["fresh"]:
        reasons.append("SECRET_SCAN_NOT_CURRENT_CLEAR")
    if ev["content_classification"] != _public_class:
        reasons.append("CONTENT_NOT_CLEARED_FOR_PUBLIC_RELEASE")
    if ev["legal_ip_review"] != _legal_public:
        reasons.append("LEGAL_IP_NOT_CLEARED_FOR_PUBLIC_RELEASE")
    if not ev["open_work"]["fresh"]:
        reasons.append("OPEN_WORK_SNAPSHOT_STALE")
    if not ev["dependencies"]["fresh"]:
        reasons.append("DEPENDENCY_SNAPSHOT_STALE")
    if ev["intent"] == "review_public":
        state = "PUBLICATION_REVIEW" if not reasons else "HOLD"
        return {"repository": repo["name"], "state": state, "reasons": reasons or ["SOURCE_TRUSTED_PUBLICATION_REVIEW_EVIDENCE_COMPLETE"], "branch_sha": sha}
    if ev["intent"] == "review_archive":
        if not ev["archive_authorized"]:
            reasons.append("ARCHIVE_AUTHORITY_NOT_PROVEN")
        elif ev["archive_authority_ref"] not in _trusted_archive_refs:
            reasons.append("ARCHIVE_AUTHORITY_NOT_SOURCE_TRUSTED")
        if any(ev["open_work"][k] for k in ("open_prs", "open_issues", "active_claims")):
            reasons.append("OPEN_WORK_BLOCKS_ARCHIVE")
        if ev["dependencies"]["consumer_count"]:
            reasons.append("ACTIVE_CONSUMERS_BLOCK_ARCHIVE")
        if ev["dependencies"]["replacement_repository"] is not None and not ev["dependencies"]["replacement_verified"]:
            reasons.append("REPLACEMENT_RELATION_UNVERIFIED")
        state = "ARCHIVE_REVIEW" if not reasons else "HOLD"
        return {"repository": repo["name"], "state": state, "reasons": reasons or ["SOURCE_TRUSTED_ARCHIVE_REVIEW_EVIDENCE_COMPLETE"], "branch_sha": sha}
    raise EstateError("unreachable evidence intent")


def _compile_at(
    snapshot: Any,
    evidence: Any,
    *,
    now: datetime,
    _trusted_owner_refs: frozenset[str] = frozenset(),
    _trusted_archive_refs: frozenset[str] = frozenset(),
    _authority_generation: tuple[tuple[str, bool], ...] = _AUTHORITY_GENERATION,
    _decision_generation = _decision,
    _validate_snapshot_generation = validate_snapshot,
    _validate_evidence_generation = validate_evidence,
    _canonical_json_generation = canonical_json,
    _loads_strict_generation = loads_strict,
    _sha256_generation = sha256_json,
    _canon_time_generation = _canon_time,
    _time_generation = _time,
    _max_age: timedelta = timedelta(days=7),
    _packet_schema: str = "commons.repo-estate.rationalizer/v1",
) -> dict[str, Any]:
    snap = _validate_snapshot_generation(snapshot)
    if now.tzinfo is None or now.utcoffset() is None:
        raise EstateError("trusted current time must be timezone-aware")
    current = now.astimezone(UTC)
    snap_time = _time_generation(snap["captured_at"], "snapshot.captured_at")
    if snap_time > current or current - snap_time > _max_age:
        raise EstateError("repository snapshot is stale or from the future")

    # Freeze one exact caller generation, validate it again, and sort evidence
    # rows before hashing so source identity is semantic rather than list-order
    # dependent.
    evmap = _validate_evidence_generation(evidence, current)
    frozen_evidence = _loads_strict_generation(_canonical_json_generation(evidence))
    frozen_evmap = _validate_evidence_generation(frozen_evidence, current)
    if frozen_evmap != evmap:
        raise EstateError("evidence changed while being frozen")
    frozen_evidence["repositories"].sort(key=lambda row: row["repository"].casefold())

    names = {r["name"].casefold() for r in snap["repositories"]}
    extras = sorted(ev["repository"] for key, ev in evmap.items() if key not in names)
    if extras:
        raise EstateError(f"evidence references repositories absent from snapshot: {extras}")
    decisions = [
        _decision_generation(
            repo,
            evmap.get(repo["name"].casefold()),
            _trusted_owner_refs=_trusted_owner_refs,
            _trusted_archive_refs=_trusted_archive_refs,
        )
        for repo in snap["repositories"]
    ]
    counts: dict[str, int] = {}
    for d in decisions:
        counts[d["state"]] = counts.get(d["state"], 0) + 1
    private_count = sum(r["visibility"] == "private" for r in snap["repositories"])
    public_count = len(snap["repositories"]) - private_count
    packet: dict[str, Any] = {
        "schema": _packet_schema,
        "evaluated_at": _canon_time_generation(current),
        "owner": snap["owner"],
        "source": {
            "snapshot_sha256": _sha256_generation(snap),
            "evidence_sha256": _sha256_generation(frozen_evidence),
            "snapshot_captured_at": snap["captured_at"],
        },
        "estate": {
            "repository_count": len(snap["repositories"]),
            "private_repository_count": private_count,
            "public_repository_count": public_count,
            "state_counts": dict(sorted(counts.items())),
        },
        "decisions": decisions,
        "authority": dict(_authority_generation),
    }
    packet["packet_sha256"] = _sha256_generation(packet)
    return packet

def compile_packet(snapshot: Any, evidence: Any) -> dict[str, Any]:
    return _compile_at(snapshot, evidence, now=datetime.now(UTC))


def verify_packet(
    packet: Any,
    snapshot: Any,
    evidence: Any,
    *,
    _authority_generation: tuple[tuple[str, bool], ...] = _AUTHORITY_GENERATION,
    _plain_generation = _plain,
    _sha256_generation = sha256_json,
    _time_generation = _time,
    _compile_generation = _compile_at,
    _clock = datetime,
    _max_age: timedelta = timedelta(days=7),
) -> bool:
    try:
        obj = _plain_generation(packet, "packet")
        if obj.get("authority") != dict(_authority_generation):
            return False
        receipt = obj.get("packet_sha256")
        if type(receipt) is not str or len(receipt) != 64 or any(c not in "0123456789abcdef" for c in receipt):
            return False
        unsigned = dict(obj)
        unsigned.pop("packet_sha256", None)
        if _sha256_generation(unsigned) != receipt:
            return False
        evaluated = _time_generation(obj.get("evaluated_at"), "packet.evaluated_at")
        now = _clock.now(UTC)
        if evaluated > now or now - evaluated > _max_age:
            return False
        return obj == _compile_generation(snapshot, evidence, now=evaluated)
    except (EstateError, TypeError, ValueError):
        return False

def render_markdown(packet: Any) -> str:
    obj = _plain(packet, "packet")
    if obj.get("schema") != PACKET_SCHEMA:
        raise EstateError("packet schema mismatch")
    estate = _plain(obj.get("estate"), "packet.estate")
    lines = [
        "# Repository Estate Rationalizer",
        "",
        f"- repositories: **{estate['repository_count']}**",
        f"- private: **{estate['private_repository_count']}**",
        f"- public: **{estate['public_repository_count']}**",
        f"- evaluated_at: `{obj['evaluated_at']}`",
        "",
        "## Decisions",
    ]
    for row in obj.get("decisions", []):
        reasons = ", ".join(row["reasons"])
        lines.append(f"- `{row['repository']}` — **{row['state']}** — {reasons}")
    lines += [
        "",
        "This is advisory decision support only. It does not authorize repository visibility, archive/delete, branch, Actions, billing, or spend mutations.",
        "A PUBLICATION_REVIEW or ARCHIVE_REVIEW state is not a safety certification; a human/operator must still perform the separate irreversible repository action.",
        f"Packet SHA-256: `{obj['packet_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def _open_parent(path: Path, *, create: bool = False) -> int:
    if not path.name or path.name in {".", ".."}:
        raise EstateError("path must name a file")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        raise EstateError("platform lacks descriptor-safe directory flags")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | nofollow | directory
    try:
        return os.open(path.parent, flags)
    except OSError as exc:
        raise EstateError(f"cannot pin parent directory for {path}: {exc}") from exc


def _read_regular(path: Path) -> bytes:
    pfd = _open_parent(path)
    try:
        try:
            before = os.stat(path.name, dir_fd=pfd, follow_symlinks=False)
        except OSError as exc:
            raise EstateError(f"cannot inspect {path}: {exc}") from exc
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise EstateError(f"{path.name} must be a bounded regular file")
        nofollow = getattr(os, "O_NOFOLLOW", None)
        nonblock = getattr(os, "O_NONBLOCK", None)
        if nofollow is None or nonblock is None:
            raise EstateError("platform lacks descriptor-safe file flags")
        fd = os.open(
            path.name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | nofollow | nonblock,
            dir_fd=pfd,
        )
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino, before.st_size) != (opened.st_dev, opened.st_ino, opened.st_size):
                raise EstateError(f"{path.name} changed while opening")
            data = bytearray()
            while True:
                chunk = os.read(fd, min(131072, MAX_FILE_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > MAX_FILE_BYTES:
                    raise EstateError(f"{path.name} is too large")
            after = os.fstat(fd)
            linked = os.stat(path.name, dir_fd=pfd, follow_symlinks=False)
            generation = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
            if generation != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise EstateError(f"{path.name} changed while reading")
            if (linked.st_dev, linked.st_ino, linked.st_size) != (opened.st_dev, opened.st_ino, opened.st_size):
                raise EstateError(f"{path.name} pathname changed while reading")
            return bytes(data)
        finally:
            os.close(fd)
    finally:
        os.close(pfd)

def _load(path: Path) -> dict[str, Any]:
    try:
        return _plain(loads_strict(_read_regular(path).decode("utf-8")), path.name)
    except UnicodeDecodeError as exc:
        raise EstateError(f"{path.name} is not UTF-8") from exc


def _write_exclusive(path: Path, text: str) -> None:
    pfd = _open_parent(path, create=True)
    try:
        try:
            os.stat(path.name, dir_fd=pfd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise EstateError(f"cannot inspect output {path}: {exc}") from exc
        else:
            raise EstateError(f"output already exists: {path}")

        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nofollow is None:
            raise EstateError("platform lacks O_NOFOLLOW")
        fd = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | nofollow,
            0o600,
            dir_fd=pfd,
        )
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):
                raise EstateError("created output is not a regular file")
            data = text.encode("utf-8")
            view = memoryview(data)
            while view:
                n = os.write(fd, view)
                if n <= 0:
                    raise EstateError("short write")
                view = view[n:]
            os.fsync(fd)
            after = os.fstat(fd)
            linked = os.stat(path.name, dir_fd=pfd, follow_symlinks=False)
            if (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino):
                raise EstateError("output descriptor generation changed")
            if (linked.st_dev, linked.st_ino) != (opened.st_dev, opened.st_ino):
                raise EstateError("output pathname changed while writing")
        finally:
            # Never unlink an uncertain pathname on failure. A partial file is
            # retained fail-closed for explicit operator inspection.
            os.close(fd)
    finally:
        os.close(pfd)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--snapshot", type=Path, required=True)
    c.add_argument("--evidence", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--markdown", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--snapshot", type=Path, required=True)
    v.add_argument("--evidence", type=Path, required=True)
    v.add_argument("--packet", type=Path, required=True)
    v.add_argument("--markdown", type=Path)
    args = p.parse_args(argv)
    try:
        snapshot = _load(args.snapshot)
        evidence = _load(args.evidence)
        if args.cmd == "compile":
            packet = compile_packet(snapshot, evidence)
            _write_exclusive(args.out, json.dumps(packet, indent=2, sort_keys=True, allow_nan=False) + "\n")
            _write_exclusive(args.markdown, render_markdown(packet))
            print(packet["packet_sha256"])
            return 0
        packet = _load(args.packet)
        if not verify_packet(packet, snapshot, evidence):
            print("REFUSED: packet verification failed", file=sys.stderr)
            return 2
        if args.markdown is not None and _read_regular(args.markdown).decode("utf-8") != render_markdown(packet):
            print("REFUSED: markdown does not match packet", file=sys.stderr)
            return 2
        print("VERIFIED")
        return 0
    except EstateError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
