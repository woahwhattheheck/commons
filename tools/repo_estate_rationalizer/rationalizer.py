#!/usr/bin/env python3
"""Deterministic advisory rationalizer for a GitHub repository estate."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.repo_estate_rationalizer.schema import *
from tools.repo_estate_rationalizer.schema import _canon_time, _plain, _time
def _decision(repo: dict[str, Any], ev: dict[str, Any] | None) -> dict[str, Any]:
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
    if ev["intent"] == "keep_private":
        if not ev["owner_authorized"]:
            reasons.append("OWNER_AUTHORITY_NOT_PROVEN")
        return {"repository": repo["name"], "state": "KEEP_PRIVATE" if not reasons else "HOLD", "reasons": reasons or ["OWNER_KEEP_PRIVATE"], "branch_sha": sha}
    if not ev["owner_authorized"]:
        reasons.append("OWNER_AUTHORITY_NOT_PROVEN")
    if ev["secret_scan"]["result"] != SECRET_CLEAR or not ev["secret_scan"]["fresh"]:
        reasons.append("SECRET_SCAN_NOT_CURRENT_CLEAR")
    if ev["content_classification"] != PUBLIC_CLASS:
        reasons.append("CONTENT_NOT_CLEARED_FOR_PUBLIC_RELEASE")
    if ev["legal_ip_review"] != LEGAL_PUBLIC:
        reasons.append("LEGAL_IP_NOT_CLEARED_FOR_PUBLIC_RELEASE")
    if not ev["open_work"]["fresh"]:
        reasons.append("OPEN_WORK_SNAPSHOT_STALE")
    if not ev["dependencies"]["fresh"]:
        reasons.append("DEPENDENCY_SNAPSHOT_STALE")
    if ev["intent"] == "review_public":
        state = "PUBLICATION_REVIEW" if not reasons else "HOLD"
        return {"repository": repo["name"], "state": state, "reasons": reasons or ["EXPLICIT_PUBLICATION_REVIEW_EVIDENCE_COMPLETE"], "branch_sha": sha}
    if ev["intent"] == "review_archive":
        if not ev["archive_authorized"]:
            reasons.append("ARCHIVE_AUTHORITY_NOT_PROVEN")
        if any(ev["open_work"][k] for k in ("open_prs", "open_issues", "active_claims")):
            reasons.append("OPEN_WORK_BLOCKS_ARCHIVE")
        if ev["dependencies"]["consumer_count"]:
            reasons.append("ACTIVE_CONSUMERS_BLOCK_ARCHIVE")
        if ev["dependencies"]["replacement_repository"] is not None and not ev["dependencies"]["replacement_verified"]:
            reasons.append("REPLACEMENT_RELATION_UNVERIFIED")
        state = "ARCHIVE_REVIEW" if not reasons else "HOLD"
        return {"repository": repo["name"], "state": state, "reasons": reasons or ["EXPLICIT_ARCHIVE_REVIEW_EVIDENCE_COMPLETE"], "branch_sha": sha}
    raise EstateError("unreachable evidence intent")


def _compile_at(snapshot: Any, evidence: Any, *, now: datetime) -> dict[str, Any]:
    snap = validate_snapshot(snapshot)
    if now.tzinfo is None or now.utcoffset() is None:
        raise EstateError("trusted current time must be timezone-aware")
    current = now.astimezone(UTC)
    snap_time = _time(snap["captured_at"], "snapshot.captured_at")
    if snap_time > current or current - snap_time > MAX_EVIDENCE_AGE:
        raise EstateError("repository snapshot is stale or from the future")
    evmap = validate_evidence(evidence, current)
    names = {r["name"].casefold() for r in snap["repositories"]}
    extras = sorted(ev["repository"] for key, ev in evmap.items() if key not in names)
    if extras:
        raise EstateError(f"evidence references repositories absent from snapshot: {extras}")
    decisions = [_decision(repo, evmap.get(repo["name"].casefold())) for repo in snap["repositories"]]
    counts: dict[str, int] = {}
    for d in decisions:
        counts[d["state"]] = counts.get(d["state"], 0) + 1
    private_count = sum(r["visibility"] == "private" for r in snap["repositories"])
    public_count = len(snap["repositories"]) - private_count
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "evaluated_at": _canon_time(current),
        "owner": snap["owner"],
        "source": {
            "snapshot_sha256": sha256_json(snap),
            "evidence_sha256": sha256_json(evidence),
            "snapshot_captured_at": snap["captured_at"],
        },
        "estate": {
            "repository_count": len(snap["repositories"]),
            "private_repository_count": private_count,
            "public_repository_count": public_count,
            "state_counts": dict(sorted(counts.items())),
        },
        "decisions": decisions,
        "authority": dict(AUTHORITY),
    }
    packet["packet_sha256"] = sha256_json(packet)
    return packet


def compile_packet(snapshot: Any, evidence: Any) -> dict[str, Any]:
    return _compile_at(snapshot, evidence, now=datetime.now(UTC))


def verify_packet(packet: Any, snapshot: Any, evidence: Any) -> bool:
    try:
        obj = _plain(packet, "packet")
        receipt = obj.get("packet_sha256")
        if type(receipt) is not str or SHA256_RE.fullmatch(receipt) is None:
            return False
        unsigned = dict(obj)
        unsigned.pop("packet_sha256", None)
        if sha256_json(unsigned) != receipt:
            return False
        evaluated = _time(obj.get("evaluated_at"), "packet.evaluated_at")
        now = datetime.now(UTC)
        if evaluated > now or now - evaluated > MAX_EVIDENCE_AGE:
            return False
        return obj == _compile_at(snapshot, evidence, now=evaluated)
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


def _read_regular(path: Path) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise EstateError(f"cannot inspect {path}: {exc}") from exc
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise EstateError(f"{path.name} must be a bounded regular file")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise EstateError("platform lacks O_NOFOLLOW")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | nofollow)
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
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise EstateError(f"{path.name} changed while reading")
        return bytes(data)
    finally:
        os.close(fd)


def _load(path: Path) -> dict[str, Any]:
    try:
        return _plain(loads_strict(_read_regular(path).decode("utf-8")), path.name)
    except UnicodeDecodeError as exc:
        raise EstateError(f"{path.name} is not UTF-8") from exc


def _write_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise EstateError(f"output already exists: {path}")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise EstateError("platform lacks O_NOFOLLOW")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | nofollow, 0o600)
    try:
        data = text.encode("utf-8")
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise EstateError("short write")
            view = view[n:]
        os.fsync(fd)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    finally:
        os.close(fd)


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
            try:
                _write_exclusive(args.markdown, render_markdown(packet))
            except Exception:
                try:
                    args.out.unlink()
                except OSError:
                    pass
                raise
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
