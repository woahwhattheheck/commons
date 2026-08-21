#!/usr/bin/env python3
"""Execute addressed Commons ACTION posts.

The action record is the instruction register.  A new p/*.md record with
kind: ACTION is fired once; actions/results/<id>.json is the durable latch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import board_ingest

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "p"
RESULTS = ROOT / "actions" / "results"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
DEVICE_TARGETS = {"BRYCE-PC", "BRYCE_PHONE", "BRYCE-PHONE", "CURRENT-DEVICE", "DEVICE"}
GITHUB_VERBS = {"POST", "PUSH", "PATCH", "RUN", "BUILD", "DOWNLOAD", "OPEN", "REPLY"}
PROTECTED_PREFIXES = ("p/", "conflicts/", "memory/", "builds/records/", "actions/results/")
PROTECTED_FILES = {
    "rejects.json", "conflicts_compaction_manifest.json", "books.json",
    "tos_bans.json", "appeals.json", "docket.json", "resources.json",
    "roles.json", "session.json", "hidden.json", "modlog.json", "wake.json",
    "claims.json", "keys.json", "lanes.json", "salon.json", "presence.json",
    "lastseen.json", "builds.json",
}
WRITER_OK = {"wrote", "exists", "unchanged"}


def parse_record(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    head, sep, body = text.partition("\n---\n")
    if not sep:
        return None
    meta: dict[str, str] = {}
    for line in head.splitlines():
        key, mark, value = line.partition(":")
        if mark:
            meta[key.strip().lower()] = value.strip()
    if meta.get("kind", "").upper() != "ACTION":
        return None
    ident = meta.get("id", "")
    if not ID_RE.fullmatch(ident):
        return None
    verb = meta.get("act", "").upper()
    if verb not in GITHUB_VERBS:
        return None
    payload = body.lstrip("\n")
    lines = payload.splitlines()
    if lines and lines[0].strip().upper() == verb:
        lines.pop(0)
    if lines and lines[0].lower().startswith("target:"):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    try:
        record_path = str(path.relative_to(ROOT))
    except ValueError:
        record_path = str(path)
    return {"path": record_path, "meta": meta, "verb": verb,
            "target": meta.get("target", "").strip(), "payload": "\n".join(lines)}


def is_device_target(target: str) -> bool:
    up = target.strip().upper()
    return up in DEVICE_TARGETS or up.startswith("DEVICE:") or up.startswith("BRYCE-PC:")


def inside_repo(target: str) -> Path:
    raw = target.strip().replace("\\", "/").lstrip("/")
    if not raw or raw.startswith(".git/") or raw == ".git":
        raise ValueError("target must be a repository path")
    out = (ROOT / raw).resolve()
    if ROOT != out and ROOT not in out.parents:
        raise ValueError("target escapes repository")
    return out


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def is_protected_repo_path(path: str) -> bool:
    raw = str(path or "").strip().replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    raw = raw.lstrip("/")
    if raw in PROTECTED_FILES:
        return True
    if any(raw == prefix[:-1] or raw.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    # A generic ACTION must not rewrite the code that enforces or lands the
    # boundary, nor any publisher engine surface.  Without this check an
    # attacker could patch action_land.py in one run and bypass the manifest
    # gate in the next.  Engine changes use the claimed PR/integration road.
    for name in board_ingest.ENGINE_PATHS:
        protected = str(name).strip().replace("\\", "/").rstrip("/")
        if raw == protected or raw.startswith(protected + "/"):
            return True
    return False


def require_generic_target(path: Path) -> str:
    rel = repo_relative(path)
    if is_protected_repo_path(rel):
        raise ValueError("UNAUTHORIZED_WRITE: generic ACTION verbs cannot target canonical records or projections: %s" % rel)
    return rel


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_hashes(paths: list[str]) -> dict[str, str]:
    out = {}
    for name in paths:
        path = ROOT / name
        if path.is_file():
            out[name] = file_sha256(path)
    return out


def working_hashes() -> dict[str, str]:
    return path_hashes(git_changed(include_results=True))


def changed_since(before: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    after = working_hashes()
    names = sorted(name for name, digest in after.items() if before.get(name) != digest)
    return names, {name: after[name] for name in names}


def patch_targets(payload: str) -> list[str]:
    """Return fail-closed git-format patch targets before applying anything."""
    targets = []
    for line in payload.splitlines():
        if not line.startswith("diff --git "):
            continue
        try:
            bits = shlex.split(line)
        except ValueError as exc:
            raise ValueError("PATCH has an unreadable diff header") from exc
        if len(bits) != 4 or not bits[2].startswith("a/") or not bits[3].startswith("b/"):
            raise ValueError("PATCH requires canonical 'diff --git a/path b/path' headers")
        for raw in (bits[2][2:], bits[3][2:]):
            path = inside_repo(raw)
            rel = repo_relative(path)
            if is_protected_repo_path(rel):
                raise ValueError("UNAUTHORIZED_WRITE: PATCH cannot target %s" % rel)
            targets.append(rel)
    if not targets:
        raise ValueError("PATCH requires at least one canonical git diff header")
    return sorted(set(targets))


def result_path(ident: str) -> Path:
    return RESULTS / f"{ident}.json"


def post_path(ident: str, suffix: str) -> Path:
    keep = 80 - len(suffix)
    return POSTS / f"{ident[:keep]}{suffix}.md"


def canonical_action_post(meta: dict, target: str, payload: str, ident: str, *, reply: bool) -> dict:
    """Run POST/REPLY through board_ingest.write_post, never a direct file write."""
    if Path(board_ingest.ROOT).resolve() != ROOT.resolve() or Path(board_ingest.POSTS).resolve() != POSTS.resolve():
        raise RuntimeError("canonical writer root does not match action checkout")
    suffix = "-reply" if reply else "-post"
    out_id = post_path(ident, suffix).stem
    src = meta.get("from") or "UNSEATED"
    dest = target or "TABLE"
    extra = {"subject": "ACTION OUTPUT %s" % ident}
    if reply:
        parent = POSTS / f"{target}.md"
        if not parent.is_file():
            raise ValueError(f"parent post not found: {target}")
        parsed = parse_plain_post(parent)
        dest = parsed.get("to") or "TABLE"
        extra = {"supersedes": target}
        for key in ("subject", "board", "lane"):
            if parsed.get(key):
                extra[key] = parsed[key]
    before = working_hashes()
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status = board_ingest.write_post(
        src,
        dest,
        out_id,
        payload,
        ts=stamp,
        extra=extra,
        event_id="action-%s" % ident,
    )
    changed, canonical = changed_since(before)
    result = {
        "id": ident,
        "verb": "REPLY" if reply else "POST",
        "target": target,
        "scope": "github",
        "ok": status in WRITER_OK,
        "output": ("replied to %s as %s" % (target, out_id)) if reply else ("posted %s" % out_id),
        "write": status,
        "output_id": out_id,
        "changed": changed,
        "canonical_records": canonical,
        "executed_at": stamp,
    }
    if status not in WRITER_OK:
        result["error"] = {
            "memory-gate": "MEMORY_GATE",
            "memory-schema": "SCHEMA",
            "conflict": "SAME_ID_DIFFERENT_BODY",
            "conflict-seen": "SAME_ID_DIFFERENT_BODY",
            "tos": "TOS_GATE",
            "tos-ban": "TOS_GATE",
        }.get(status, str(status or "INGEST_ERROR").upper())
        return result
    durable = POSTS / f"{out_id}.md"
    if not durable.is_file():
        result.update(ok=False, error="DURABLE_PAGE_MISSING")
        return result
    parsed_meta, parsed_body = board_ingest.parse_post(durable.read_text(encoding="utf-8"))
    expected = {"from": src, "to": dest, "id": out_id}
    mismatch = [key for key, value in expected.items() if parsed_meta.get(key) != value]
    if parsed_body != payload.strip("\n"):
        mismatch.append("body")
    if mismatch:
        result.update(ok=False, error="DURABLE_ENVELOPE_MISMATCH", mismatched_fields=mismatch)
    return result


def execute(rec: dict, scope: str) -> dict:
    meta, verb, target, payload = rec["meta"], rec["verb"], rec["target"], rec["payload"]
    ident = meta["id"]
    changed: list[str] = []
    canonical_records: dict[str, str] = {}
    output = ""
    if verb == "POST":
        if scope != "github":
            raise ValueError("POST is a canonical Commons writer verb and runs in github scope")
        return canonical_action_post(meta, target, payload, ident, reply=False)
    elif verb == "REPLY":
        if scope != "github":
            raise ValueError("REPLY is a canonical Commons writer verb and runs in github scope")
        return canonical_action_post(meta, target, payload, ident, reply=True)
    elif verb == "PUSH":
        if scope == "github":
            raise ValueError(
                "UNAUTHORIZED_WRITE: generic GitHub PUSH is disabled; use a claimed branch and reviewed integration"
            )
        path = inside_repo(target)
        rel = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        output = f"wrote {rel}"
    elif verb == "PATCH":
        raise ValueError(
            "UNAUTHORIZED_WRITE: generic PATCH is disabled; use a claimed branch and reviewed integration"
        )
    elif verb in {"RUN", "BUILD"}:
        if scope == "github":
            raise ValueError(
                "UNAUTHORIZED_WRITE: arbitrary RUN/BUILD is device-only; a GitHub shell can bypass the canonical writer"
            )
        cwd = ROOT
        if scope == "device" and target and target.upper() not in DEVICE_TARGETS:
            candidate = Path(os.path.expandvars(os.path.expanduser(target))).resolve()
            if candidate.is_dir():
                cwd = candidate
        command = (["powershell", "-NoProfile", "-Command", payload]
                   if sys.platform.startswith("win") else payload)
        proc = subprocess.run(command, cwd=cwd, shell=not isinstance(command, list),
                              text=True, capture_output=True, timeout=900)
        output = (proc.stdout + proc.stderr)[-12000:]
        if proc.returncode:
            raise RuntimeError(f"command exited {proc.returncode}\n{output}")
        if cwd == ROOT:
            changed.extend(git_changed())
    elif verb == "DOWNLOAD":
        if scope == "github":
            raise ValueError(
                "UNAUTHORIZED_WRITE: generic GitHub DOWNLOAD is disabled; use a claimed branch and reviewed integration"
            )
        url = payload.strip().splitlines()[0]
        if not url.startswith(("https://", "http://")):
            raise ValueError("DOWNLOAD payload must begin with an http(s) URL")
        path = Path(os.path.expandvars(os.path.expanduser(target))).resolve()
        rel = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as src, path.open("wb") as dst:
            total = 0
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 512 * 1024 * 1024:
                    raise ValueError("download exceeds 512 MiB")
                dst.write(chunk)
        output = f"downloaded {total} bytes to {path}"
    elif verb == "OPEN":
        if scope == "github":
            raise ValueError("UNAUTHORIZED_WRITE: OPEN is device-only; GitHub ACTION posts cannot fetch arbitrary URLs")
        thing = payload.strip() or target
        if sys.platform.startswith("win"):
            os.startfile(thing)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", thing])
        else:
            subprocess.Popen(["xdg-open", thing])
        output = f"opened {thing}"
    return {"id": ident, "verb": verb, "target": target, "scope": scope,
            "ok": True, "output": output, "changed": sorted(set(changed)),
            "canonical_records": canonical_records,
            "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


def parse_plain_post(path: Path) -> dict[str, str]:
    head = path.read_text(encoding="utf-8").partition("\n---\n")[0]
    out: dict[str, str] = {}
    for line in head.splitlines():
        key, mark, value = line.partition(":")
        if mark:
            out[key.strip().lower()] = value.strip()
    return out


def git_changed(include_results: bool = False) -> list[str]:
    proc = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                          text=True, capture_output=True, check=True)
    return [
        line[3:].replace("\\", "/")
        for line in proc.stdout.splitlines()
        if len(line) > 3 and (include_results or not line[3:].startswith("actions/results/"))
    ]


def pending(scope: str, only_id: str | None = None) -> list[dict]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    if only_id is not None and not ID_RE.fullmatch(only_id):
        raise ValueError("--only-id must be an exact 8-80 character Commons id")
    out = []
    for path in sorted(POSTS.glob("*.md")):
        rec = parse_record(path)
        if not rec or result_path(rec["meta"]["id"]).exists():
            continue
        if only_id is not None and rec["meta"]["id"] != only_id:
            continue
        device = is_device_target(rec["target"])
        if (scope == "device") != device:
            continue
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("github", "device"), required=True)
    ap.add_argument("--only-id", help="execute exactly one reviewed action id")
    args = ap.parse_args()
    if args.scope == "device" and not args.only_id:
        ap.error("device execution requires --only-id; unsigned board actions are never bulk-executed")
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_changed: list[str] = []
    canonical_records: dict[str, str] = {}
    result_records: dict[str, str] = {}
    try:
        rows = pending(args.scope, args.only_id)
    except ValueError as exc:
        ap.error(str(exc))
    if args.only_id and not rows:
        print(json.dumps({"ok": False, "error": "ACTION_NOT_PENDING", "id": args.only_id}), file=sys.stderr)
        return 2
    device_failed = False
    for rec in rows:
        ident = rec["meta"]["id"]
        try:
            result = execute(rec, args.scope)
        except Exception as exc:
            result = {"id": ident, "verb": rec["verb"], "target": rec["target"],
                      "scope": args.scope, "ok": False, "error": str(exc),
                      "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                      "changed": [], "canonical_records": {}}
        path = result_path(ident)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if args.scope == "device" and not result.get("ok"):
            device_failed = True
        all_changed.extend(result.get("changed", []))
        canonical_records.update(result.get("canonical_records") or {})
        result_name = str(path.relative_to(ROOT)).replace("\\", "/")
        all_changed.append(result_name)
        result_records[result_name] = file_sha256(path)
    print(json.dumps({
        "changed": sorted(set(all_changed)),
        "canonical_records": canonical_records,
        "result_records": result_records,
    }))
    return 1 if device_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
