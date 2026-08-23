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
import muhlnickel_spec_guard

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
ACTION_DOOR_PATHS = {
    "index.html", "action.html", "action_executor.py", "action_land.py",
    "board_ingest.py", "memory_board.py", "capability_declaration.py",
    ".capability-declaration-live", "GRANTS.md", "AGENTS.md", "START.md", "ENTRY.md",
    "WRITING.md", "ground/OPEN_DOOR.md", "ground/ACTION_DOOR.md",
    "ground/PICK.md", "test_action_executor.py", "test_write_roads.py",
    "muhlnickel_spec_guard.py", "test_muhlnickel_spec_guard.py",
    "ground/muhlnickel-observe-tools.json", "host/pfc_preflight.py",
    "infra/host/pfc_preflight.py", "infra/OUT_OF_SPEC_NOT_INCLUDED.txt",
    ".github/workflows/commons-action-executor.yml",
    ".github/workflows/commons-board.yml",
    ".github/workflows/commons-device-executor.yml",
    ".github/workflows/muhlnickel-spec-guard.yml",
    ".github/workflows/tests.yml",
    ".agents/skills/write-roads/SKILL.md",
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
    if raw in ACTION_DOOR_PATHS:
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


def git_status_entries(include_results: bool = False) -> list[tuple[str, str]]:
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=ROOT, capture_output=True, check=True,
    )
    out = []
    rows = proc.stdout.decode("utf-8", "surrogateescape").split("\0")
    i = 0
    while i < len(rows):
        row = rows[i]
        i += 1
        if len(row) <= 3:
            continue
        status, name = row[:2], row[3:].replace("\\", "/")
        if "R" in status or "C" in status:
            old = rows[i].replace("\\", "/") if i < len(rows) else ""
            i += 1
            if old:
                out.append(("D ", old))
            status = "A "
        if not include_results and name.startswith("actions/results/"):
            continue
        out.append((status, name))
    return out


def working_state() -> dict[str, str | None]:
    state: dict[str, str | None] = {}
    for status, name in git_status_entries():
        path = ROOT / name
        state[name] = None if "D" in status or not path.exists() else file_sha256(path)
    return state


def collect_action_outputs(before: dict[str, str | None]) -> tuple[list[str], dict[str, str], list[str]]:
    """Hash ordinary outputs and explicitly carry ordinary deletions."""
    outputs: dict[str, str] = {}
    deletions: list[str] = []
    after = working_state()
    missing = object()
    for name in sorted(set(before) | set(after)):
        if before.get(name, missing) == after.get(name, missing):
            continue
        path = ROOT / name
        if after.get(name, missing) is None:
            rel = require_generic_target(path)
            deletions.append(rel)
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("UNAUTHORIZED_WRITE: hosted script output must be a regular file: %s" % name)
        rel = require_generic_target(path)
        digest = file_sha256(path)
        outputs[rel] = digest
    changed = sorted(set(outputs) | set(deletions))
    return changed, outputs, sorted(set(deletions))


def hosted_python_command(payload: str) -> list[str]:
    """Parse one checked-in Python invocation without a shell or inline code."""
    try:
        parts = shlex.split(payload)
    except ValueError as exc:
        raise ValueError("RUN/BUILD payload is not a readable argv") from exc
    if len(parts) < 2 or parts[0] not in {"python", "python3"}:
        raise ValueError("RUN/BUILD on GitHub must be: python3 path/to/tracked.py [literal argv]")
    if parts[1].startswith("-") or not parts[1].endswith(".py"):
        raise ValueError("RUN/BUILD requires a checked-in .py script; -c and -m are not allowed")
    script = inside_repo(parts[1])
    rel = require_generic_target(script)
    if script.is_symlink() or not script.is_file():
        raise ValueError("RUN/BUILD script must be a regular checked-in file: %s" % rel)
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel], cwd=ROOT,
        text=True, capture_output=True,
    )
    if tracked.returncode:
        raise ValueError("RUN/BUILD script must already be checked in: %s" % rel)
    # RUN/BUILD is useful and remains open for ordinary repository work.  It
    # must not turn an existing Muhlnickel runtime into host computation.  The
    # semantic check follows local imports and behavior, not this filename.
    old_root = muhlnickel_spec_guard.ROOT
    try:
        muhlnickel_spec_guard.ROOT = ROOT
        spec_errors = muhlnickel_spec_guard.executable_violations(rel, "HEAD")
    finally:
        muhlnickel_spec_guard.ROOT = old_root
    if spec_errors:
        raise ValueError(muhlnickel_spec_guard.WARNING + "\n" + "\n".join(spec_errors))
    return [sys.executable, rel, *parts[2:]]


def preflight_open_command(payload: str) -> None:
    old_root = muhlnickel_spec_guard.ROOT
    try:
        muhlnickel_spec_guard.ROOT = ROOT
        errors = muhlnickel_spec_guard.command_violations(payload, "HEAD")
    finally:
        muhlnickel_spec_guard.ROOT = old_root
    if errors:
        raise ValueError(muhlnickel_spec_guard.WARNING + "\n" + "\n".join(errors))


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
    for key in ("is_language_model", "model", "harness", "tools", "resources"):
        if meta.get(key):
            extra[key] = meta[key]
    durable = POSTS / f"{out_id}.md"
    expected = {"from": src, "to": dest, "id": out_id}
    replay_expected = {**expected, **extra}
    expected_body = payload.strip("\n")
    if durable.is_file():
        parsed_meta, parsed_body = board_ingest.parse_post(durable.read_text(encoding="utf-8"))
        mismatch = [key for key, value in replay_expected.items() if parsed_meta.get(key) != value]
        if parsed_body != expected_body:
            mismatch.append("body")
        if not mismatch:
            stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return {
                "id": ident,
                "verb": "REPLY" if reply else "POST",
                "target": target,
                "scope": "github",
                "ok": True,
                "output": ("replied to %s as %s" % (target, out_id)) if reply else ("posted %s" % out_id),
                "write": "exists",
                "output_id": out_id,
                "changed": [],
                "canonical_records": {},
                "executed_at": stamp,
            }
    before = working_hashes()
    stamp = meta.get("ts") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
            "capability-declaration": "CAPABILITY_DECLARATION",
            "conflict": "SAME_ID_DIFFERENT_BODY",
            "conflict-seen": "SAME_ID_DIFFERENT_BODY",
            "tos": "TOS_GATE",
            "tos-ban": "TOS_GATE",
        }.get(status, str(status or "INGEST_ERROR").upper())
        return result
    if not durable.is_file():
        result.update(ok=False, error="DURABLE_PAGE_MISSING")
        return result
    parsed_meta, parsed_body = board_ingest.parse_post(durable.read_text(encoding="utf-8"))
    mismatch = [key for key, value in expected.items() if parsed_meta.get(key) != value]
    if parsed_body != expected_body:
        mismatch.append("body")
    if mismatch:
        result.update(ok=False, error="DURABLE_ENVELOPE_MISMATCH", mismatched_fields=mismatch)
    return result


def execute(rec: dict, scope: str) -> dict:
    meta, verb, target, payload = rec["meta"], rec["verb"], rec["target"], rec["payload"]
    ident = meta["id"]
    changed: list[str] = []
    canonical_records: dict[str, str] = {}
    action_outputs: dict[str, str] = {}
    action_deletions: list[str] = []
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
            path = inside_repo(target)
            rel = require_generic_target(path)
            before = working_state()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
            changed, action_outputs, action_deletions = collect_action_outputs(before)
            output = f"wrote {rel}"
            return {"id": ident, "verb": verb, "target": target, "scope": scope,
                    "ok": True, "output": output, "changed": changed,
                    "canonical_records": canonical_records, "action_outputs": action_outputs,
                    "action_deletions": action_deletions,
                    "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        path = inside_repo(target)
        rel = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        output = f"wrote {rel}"
    elif verb == "PATCH":
        if scope != "github":
            raise ValueError("PATCH is a repository verb and runs in github scope")
        patch_targets(payload)
        before = working_state()
        proc = subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=ROOT,
                              input=payload, text=True, capture_output=True, timeout=180)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or "git apply failed")
        changed, action_outputs, action_deletions = collect_action_outputs(before)
        output = proc.stdout.strip() or "patch applied"
    elif verb in {"RUN", "BUILD"}:
        if scope == "github":
            preflight_open_command(payload)
            cwd = ROOT
            if target and target.upper() not in {"GITHUB", "REPO", "COMMONS"}:
                candidate = inside_repo(target)
                if candidate.is_dir():
                    cwd = candidate
            before = working_state()
            command = (["powershell", "-NoProfile", "-Command", payload]
                       if sys.platform.startswith("win") else payload)
            proc = subprocess.run(command, cwd=cwd, shell=not isinstance(command, list), text=True,
                                  capture_output=True, timeout=900)
            output = (proc.stdout + proc.stderr)[-12000:]
            if proc.returncode:
                raise RuntimeError(f"command exited {proc.returncode}\n{output}")
            changed, action_outputs, action_deletions = collect_action_outputs(before)
            return {"id": ident, "verb": verb, "target": target, "scope": scope,
                    "ok": True, "output": output, "changed": changed,
                    "canonical_records": canonical_records, "action_outputs": action_outputs,
                    "action_deletions": action_deletions,
                    "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
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
            path = inside_repo(target)
            require_generic_target(path)
            before = working_state()
        else:
            before = {}
        url = payload.strip().splitlines()[0]
        if not url.startswith(("https://", "http://")):
            raise ValueError("DOWNLOAD payload must begin with an http(s) URL")
        path = (path if scope == "github"
                else Path(os.path.expandvars(os.path.expanduser(target))).resolve())
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
        if scope == "github":
            changed, action_outputs, action_deletions = collect_action_outputs(before)
        output = f"downloaded {total} bytes to {path}"
    elif verb == "OPEN":
        thing = payload.strip() or target
        if scope == "github":
            with urllib.request.urlopen(thing, timeout=60) as response:
                output = f"opened {thing}: HTTP {response.status}"
        elif sys.platform.startswith("win"):
            os.startfile(thing)  # type: ignore[attr-defined]
            output = f"opened {thing}"
        elif sys.platform == "darwin":
            subprocess.Popen(["open", thing])
            output = f"opened {thing}"
        else:
            subprocess.Popen(["xdg-open", thing])
            output = f"opened {thing}"
    return {"id": ident, "verb": verb, "target": target, "scope": scope,
            "ok": True, "output": output, "changed": sorted(set(changed)),
            "canonical_records": canonical_records, "action_outputs": action_outputs,
            "action_deletions": action_deletions,
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
    return [name for _status, name in git_status_entries(include_results)]


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
    action_outputs: dict[str, str] = {}
    action_deletions: list[str] = []
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
                      "changed": [], "canonical_records": {}, "action_outputs": {},
                      "action_deletions": []}
        path = result_path(ident)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if args.scope == "device" and not result.get("ok"):
            device_failed = True
        all_changed.extend(result.get("changed", []))
        canonical_records.update(result.get("canonical_records") or {})
        action_outputs.update(result.get("action_outputs") or {})
        action_deletions.extend(result.get("action_deletions") or [])
        result_name = str(path.relative_to(ROOT)).replace("\\", "/")
        all_changed.append(result_name)
        result_records[result_name] = file_sha256(path)
        if args.scope == "github" and not result.get("ok") and rec["verb"] in {"RUN", "BUILD"}:
            break
    print(json.dumps({
        "changed": sorted(set(all_changed)),
        "canonical_records": canonical_records,
        "action_outputs": action_outputs,
        "action_deletions": sorted(set(action_deletions)),
        "result_records": result_records,
    }))
    return 1 if device_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
