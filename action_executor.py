#!/usr/bin/env python3
"""Execute addressed Commons ACTION posts.

The action record is the instruction register.  A new p/*.md record with
kind: ACTION is fired once.  Repository actions use actions/results/<id>.json
as their terminal latch.  Device actions additionally require a durable,
history-backed reservation before a separate read-only runner may execute.
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

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "p"
RESULTS = ROOT / "actions" / "results"
DEVICE_RESERVATIONS = ROOT / "actions" / "device-reservations"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
DEVICE_TARGETS = {"BRYCE-PC", "BRYCE_PHONE", "BRYCE-PHONE", "CURRENT-DEVICE", "DEVICE"}
MAX_ACTION_VERB_CHARS = 160
MAX_DEVICE_TARGET_CHARS = 1024
WRITER_OK = {"wrote", "exists", "unchanged"}


def _load_board_ingest():
    """Load the repository writer only for github-scope POST/REPLY work."""
    import board_ingest as module

    globals()["board_ingest"] = module
    return module


def __getattr__(name: str):
    # Preserve the historical module attribute for callers/tests without making
    # the device executor import board_ingest and its mutable dependency graph.
    if name == "board_ingest":
        return _load_board_ingest()
    raise AttributeError(name)


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
    verb = meta.get("act", "").strip().upper()
    if not verb:
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
        record_path = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        record_path = str(path)
    return {"path": record_path, "meta": meta, "verb": verb,
            "target": meta.get("target", "").strip(), "payload": "\n".join(lines)}


def is_device_target(target: str) -> bool:
    up = target.strip().upper()
    return up in DEVICE_TARGETS or up.startswith("DEVICE:") or up.startswith("BRYCE-PC:")


def resolve_target(target: str) -> Path:
    """Resolve an explicit target without confining execution to the checkout."""
    raw = os.path.expandvars(os.path.expanduser(target.strip()))
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


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
    for status, name in git_status_entries(include_results=True):
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
            rel = repo_relative(path)
            deletions.append(rel)
            continue
        if path.is_symlink() or not path.is_file():
            # The action executed. Objects that cannot be copied as regular
            # artifact files remain ephemeral instead of becoming a gate.
            continue
        rel = repo_relative(path)
        digest = file_sha256(path)
        outputs[rel] = digest
    changed = sorted(set(outputs) | set(deletions))
    return changed, outputs, sorted(set(deletions))


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
            path = resolve_target(raw)
            rel = repo_relative(path)
            targets.append(rel)
    if not targets:
        raise ValueError("PATCH requires at least one canonical git diff header")
    return sorted(set(targets))


def execute_shell_payload(target: str, payload: str, scope: str) -> tuple[str, list[str], dict[str, str], list[str]]:
    """Execute the payload for RUN/BUILD and every free-text verb."""
    cwd = ROOT
    before: dict[str, str | None] = {}
    if scope == "github":
        if target and target.upper() not in {"GITHUB", "REPO", "COMMONS"}:
            candidate = resolve_target(target)
            if candidate.is_dir():
                cwd = candidate
        before = working_state()
    elif target and target.upper() not in DEVICE_TARGETS:
        candidate = Path(os.path.expandvars(os.path.expanduser(target))).resolve()
        if candidate.is_dir():
            cwd = candidate
    command = (["powershell", "-NoProfile", "-Command", payload]
               if sys.platform.startswith("win") else payload)
    proc = subprocess.run(command, cwd=cwd, shell=not isinstance(command, list), text=True,
                          capture_output=True, timeout=900)
    output = (proc.stdout + proc.stderr)[-12000:]
    if proc.returncode:
        raise RuntimeError(f"command exited {proc.returncode}\n{output}")
    if scope == "github":
        changed, outputs, deletions = collect_action_outputs(before)
    else:
        changed = git_changed() if cwd == ROOT else []
        outputs, deletions = {}, []
    return output, changed, outputs, deletions


def result_path(ident: str) -> Path:
    return RESULTS / f"{ident}.json"


def device_reservation_path(ident: str) -> Path:
    # Derive from ROOT so isolated tests that relocate the executor cannot
    # accidentally consult the real checkout's latch directory.
    return ROOT / "actions" / "device-reservations" / f"{ident}.json"


def _path_entry_exists(path: Path) -> bool:
    """Treat every filesystem object, including a broken symlink, as a latch."""
    return os.path.lexists(path)


def _safe_state_directory(path: Path) -> bool:
    """Reject state namespaces that traverse symlinks or non-directories."""
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        # Relocated pure-test directories have no shared repository namespace.
        return True
    cursor = ROOT
    for part in rel.parts:
        cursor = cursor / part
        if not os.path.lexists(cursor):
            continue
        if cursor.is_symlink() or not cursor.is_dir():
            return False
    return True


def ever_latched(ident: str) -> bool:
    """Return whether a reservation/result exists now or in reachable HEAD history.

    The history check prevents deleting or renaming a one-shot record from
    reopening the action id.  Production workflows use full-history checkouts.
    A non-Git scratch root is supported for the executor's pure unit tests; a
    shallow Git checkout fails closed instead of pretending its partial history
    is authoritative.
    """
    paths = (result_path(ident), device_reservation_path(ident))
    if any(_path_entry_exists(path) for path in paths):
        return True
    inside = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT,
        text=True, capture_output=True,
    )
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return False
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
        text=True, capture_output=True,
    )
    if shallow.returncode != 0 or shallow.stdout.strip() != "false":
        raise RuntimeError("device/action latch history is unavailable or shallow")
    try:
        rels = [str(path.relative_to(ROOT)).replace("\\", "/") for path in paths]
    except ValueError:
        # Isolated tests may relocate POSTS/RESULTS without relocating ROOT.
        # Current filesystem latches above still apply; there is no shared Git
        # history to consult across those unrelated roots.
        return False
    seen = subprocess.run(
        ["git", "log", "--full-history", "-1", "--format=%H", "HEAD", "--", *rels], cwd=ROOT,
        text=True, capture_output=True, check=True,
    )
    return bool(seen.stdout.strip())


def post_path(ident: str, suffix: str) -> Path:
    keep = 80 - len(suffix)
    return POSTS / f"{ident[:keep]}{suffix}.md"


def canonical_action_post(meta: dict, target: str, payload: str, ident: str, *, reply: bool) -> dict:
    """Run POST/REPLY through board_ingest.write_post, never a direct file write."""
    board_ingest = _load_board_ingest()
    if Path(board_ingest.ROOT).resolve() != ROOT.resolve() or Path(board_ingest.POSTS).resolve() != POSTS.resolve():
        raise RuntimeError("canonical writer root does not match action checkout")
    suffix = "-reply" if reply else "-post"
    out_id = post_path(ident, suffix).stem
    src = meta.get("from") or "UNSEATED"
    dest = target or "TABLE"
    extra = {"subject": "ACTION OUTPUT %s" % ident, "kind": "ACTION"}
    if reply:
        parent = POSTS / f"{target}.md"
        if not parent.is_file():
            raise ValueError(f"parent post not found: {target}")
        parsed = parse_plain_post(parent)
        dest = parsed.get("to") or "TABLE"
        extra = {"supersedes": target, "kind": "ACTION"}
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
        result["error"] = str(status or "WRITER_ERROR").upper().replace("-", "_")
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
            path = resolve_target(target)
            rel = repo_relative(path)
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
        path = resolve_target(target)
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
        output, changed, action_outputs, action_deletions = execute_shell_payload(target, payload, scope)
    elif verb == "DOWNLOAD":
        if scope == "github":
            path = resolve_target(target)
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
                dst.write(chunk)
        if scope == "github":
            changed, action_outputs, action_deletions = collect_action_outputs(before)
        output = f"downloaded {total} bytes to {path}"
    elif verb == "ACTION" and not target.strip() and payload.strip() == "possessing the link is authorization":
        output = "recorded; empty fire_action is an open-door no-op"
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
    else:
        output, changed, action_outputs, action_deletions = execute_shell_payload(target, payload, scope)
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
    if only_id is not None and not ID_RE.fullmatch(only_id):
        raise ValueError("--only-id must be an exact 8-80 character Commons id")
    if not _safe_state_directory(ROOT / "actions" / "results"):
        return []
    if not _safe_state_directory(ROOT / "actions" / "device-reservations"):
        return []
    if POSTS.is_symlink() or not POSTS.is_dir():
        return []
    declared: dict[str, list[Path]] = {}
    parsed: dict[str, dict] = {}
    for path in sorted(POSTS.glob("*.md")):
        # A symlink/directory in the canonical source namespace makes the
        # snapshot ambiguous.  Fail the whole scan closed instead of following
        # attacker-selected bytes or silently ignoring an alias.
        if path.is_symlink() or not path.is_file():
            return []
        plain = parse_plain_post(path)
        declared_id = plain.get("id", "")
        if plain.get("kind", "").upper() == "ACTION" and ID_RE.fullmatch(declared_id):
            declared.setdefault(declared_id, []).append(path)
        rec = parse_record(path)
        if rec:
            parsed[str(path)] = rec

    out = []
    for ident in sorted(declared):
        paths = declared[ident]
        # A single canonical source path is part of the execution address.
        # Duplicate declarations (including an otherwise malformed duplicate)
        # and filename/id mismatches are UNKNOWN, not candidates that may race
        # through different scopes.
        if len(paths) != 1 or paths[0] != POSTS / f"{ident}.md":
            continue
        rec = parsed.get(str(paths[0]))
        if rec is None:
            continue
        if only_id is not None and ident != only_id:
            continue
        if ever_latched(ident):
            continue
        device = is_device_target(rec["target"])
        if device and (
            len(rec["verb"]) > MAX_ACTION_VERB_CHARS
            or len(rec["target"]) > MAX_DEVICE_TARGET_CHARS
            or "\n" in rec["target"]
        ):
            # Non-reservable device records are permanently UNKNOWN and must
            # not starve later canonical work in the bounded batch prefix.
            continue
        if (scope == "device") != device:
            continue
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("github", "device"), required=True)
    ap.add_argument("--only-id", help="optionally execute only this action id")
    args = ap.parse_args()
    if args.scope == "device":
        ap.error(
            "unbound device execution is disabled; use the durable "
            "device reservation workflow"
        )
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
        path.parent.mkdir(parents=True, exist_ok=True)
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
