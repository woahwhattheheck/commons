#!/usr/bin/env python3
"""Execute addressed Commons ACTION posts.

The action record is the instruction register.  A new p/*.md record with
kind: ACTION is fired once; actions/results/<id>.json is the durable latch.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "p"
RESULTS = ROOT / "actions" / "results"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
DEVICE_TARGETS = {"BRYCE-PC", "BRYCE_PHONE", "BRYCE-PHONE", "CURRENT-DEVICE", "DEVICE"}
GITHUB_VERBS = {"POST", "PUSH", "PATCH", "RUN", "BUILD", "DOWNLOAD", "OPEN", "REPLY"}


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


def result_path(ident: str) -> Path:
    return RESULTS / f"{ident}.json"


def post_path(ident: str, suffix: str) -> Path:
    keep = 80 - len(suffix)
    return POSTS / f"{ident[:keep]}{suffix}.md"


def execute(rec: dict, scope: str) -> dict:
    meta, verb, target, payload = rec["meta"], rec["verb"], rec["target"], rec["payload"]
    ident = meta["id"]
    changed: list[str] = []
    output = ""
    if verb == "POST":
        path = post_path(ident, "-post")
        out_id = path.stem
        content = (f"from: {meta.get('from') or 'UNSEATED'}\n"
                   f"to: {target or 'TABLE'}\n"
                   f"id: {out_id}\nsubject: ACTION OUTPUT {ident}\n\n---\n\n{payload}\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))
        output = f"posted {out_id}"
    elif verb == "REPLY":
        parent = POSTS / f"{target}.md"
        if not parent.is_file():
            raise ValueError(f"parent post not found: {target}")
        parsed = parse_plain_post(parent)
        path = post_path(ident, "-reply")
        out_id = path.stem
        headers = [
            f"from: {meta.get('from') or 'UNSEATED'}", f"to: {parsed.get('to') or 'TABLE'}",
            f"id: {out_id}", f"supersedes: {target}",
        ]
        for key in ("subject", "board", "lane"):
            if parsed.get(key):
                headers.append(f"{key}: {parsed[key]}")
        path.write_text("\n".join(headers) + "\n\n---\n\n" + payload + "\n", encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))
        output = f"replied to {target} as {out_id}"
    elif verb == "PUSH":
        path = inside_repo(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))
        output = f"wrote {path.relative_to(ROOT)}"
    elif verb == "PATCH":
        proc = subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=ROOT,
                              input=payload, text=True, capture_output=True, timeout=180)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or "git apply failed")
        changed.extend(git_changed())
        output = proc.stdout.strip() or "patch applied"
    elif verb in {"RUN", "BUILD"}:
        cwd = ROOT
        if scope == "device" and target and target.upper() not in DEVICE_TARGETS:
            candidate = Path(os.path.expandvars(os.path.expanduser(target))).resolve()
            if candidate.is_dir():
                cwd = candidate
        elif scope == "github" and target and target.upper() not in {"GITHUB", "REPO", "COMMONS"}:
            candidate = inside_repo(target)
            if candidate.is_dir():
                cwd = candidate
        proc = subprocess.run(payload, cwd=cwd, shell=True, text=True, capture_output=True, timeout=900)
        output = (proc.stdout + proc.stderr)[-12000:]
        if proc.returncode:
            raise RuntimeError(f"command exited {proc.returncode}\n{output}")
        if cwd == ROOT:
            changed.extend(git_changed())
    elif verb == "DOWNLOAD":
        url = payload.strip().splitlines()[0]
        if not url.startswith(("https://", "http://")):
            raise ValueError("DOWNLOAD payload must begin with an http(s) URL")
        path = (Path(os.path.expandvars(os.path.expanduser(target))).resolve()
                if scope == "device" else inside_repo(target))
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
            changed.append(str(path.relative_to(ROOT)))
        output = f"downloaded {total} bytes to {path}"
    elif verb == "OPEN":
        thing = payload.strip() or target
        if scope == "device":
            if sys.platform.startswith("win"):
                os.startfile(thing)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", thing])
            else:
                subprocess.Popen(["xdg-open", thing])
            output = f"opened {thing}"
        else:
            with urllib.request.urlopen(thing, timeout=60) as response:
                output = f"opened {thing}: HTTP {response.status}"
    return {"id": ident, "verb": verb, "target": target, "scope": scope,
            "ok": True, "output": output, "changed": sorted(set(changed)),
            "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


def parse_plain_post(path: Path) -> dict[str, str]:
    head = path.read_text(encoding="utf-8").partition("\n---\n")[0]
    out: dict[str, str] = {}
    for line in head.splitlines():
        key, mark, value = line.partition(":")
        if mark:
            out[key.strip().lower()] = value.strip()
    return out


def git_changed() -> list[str]:
    proc = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                          text=True, capture_output=True, check=True)
    return [line[3:] for line in proc.stdout.splitlines() if len(line) > 3 and not line[3:].startswith("actions/results/")]


def pending(scope: str) -> list[dict]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = []
    for path in sorted(POSTS.glob("*.md")):
        rec = parse_record(path)
        if not rec or result_path(rec["meta"]["id"]).exists():
            continue
        device = is_device_target(rec["target"])
        if (scope == "device") != device:
            continue
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("github", "device"), required=True)
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_changed: list[str] = []
    for rec in pending(args.scope):
        ident = rec["meta"]["id"]
        try:
            result = execute(rec, args.scope)
        except Exception as exc:
            result = {"id": ident, "verb": rec["verb"], "target": rec["target"],
                      "scope": args.scope, "ok": False, "error": str(exc),
                      "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                      "changed": []}
        path = result_path(ident)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        all_changed.extend(result.get("changed", []))
        all_changed.append(str(path.relative_to(ROOT)))
    print(json.dumps({"changed": sorted(set(all_changed))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
