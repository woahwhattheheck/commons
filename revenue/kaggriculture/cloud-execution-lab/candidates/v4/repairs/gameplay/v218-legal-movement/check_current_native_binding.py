#!/usr/bin/env python3
"""Fail-closed V218 current-native binding audit.

This is read-only execution/custody tooling. It does not compose, activate, or run V218.
It answers only whether an authenticated native package contains a discoverable binding
from main/runtime/config/package code to the current V218 router surface.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

TOKENS = ("r04_full_router", "v218", "movement_parity")
EXCLUDE_PARTS = {"__pycache__", ".git"}


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scan_text(path: Path, root: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    low = text.lower()
    hits = {tok: low.count(tok.lower()) for tok in TOKENS}
    if not any(hits.values()):
        return None
    return {"path": str(path.relative_to(root)), "hits": hits}


def audit(root: Path) -> dict:
    root = root.resolve()
    required = [root / "main.py", root / "titan_runtime.py", root / "TITAN-CONFIG.json"]
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    if missing:
        raise ValueError(f"missing native package files: {missing}")

    config_raw = (root / "TITAN-CONFIG.json").read_bytes()
    config = json.loads(config_raw)
    if type(config) is not dict:
        raise ValueError("TITAN-CONFIG.json must be an object")

    refs = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in EXCLUDE_PARTS for part in path.parts):
            continue
        # Package executable/config text only. Reference checks are evidence about the
        # engine, not a production binding into main.py::agent.
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] == "checks":
            continue
        if path.suffix not in {".py", ".json"}:
            continue
        scanned += 1
        hit = _scan_text(path, root)
        if hit:
            refs.append(hit)

    main = (root / "main.py").read_bytes()
    runtime = (root / "titan_runtime.py").read_bytes()
    config_v218_keys = sorted(k for k in config if "v218" in str(k).lower() or "movement_parity" in str(k).lower())
    router_refs = sum(row["hits"]["r04_full_router"] for row in refs)
    v218_refs = sum(row["hits"]["v218"] + row["hits"]["movement_parity"] for row in refs)
    wired = bool(router_refs or v218_refs or config_v218_keys)

    return {
        "schema": "titan-v4-v218-native-binding/v1",
        "native_root": str(root),
        "main": {"git_blob": git_blob(main), "sha256": sha256(main), "bytes": len(main)},
        "runtime": {"git_blob": git_blob(runtime), "sha256": sha256(runtime), "bytes": len(runtime)},
        "config": {
            "git_blob": git_blob(config_raw), "sha256": sha256(config_raw), "bytes": len(config_raw),
            "keys": sorted(config), "v218_keys": config_v218_keys,
        },
        "package_text_files_scanned": scanned,
        "binding_refs": refs,
        "router_ref_count": router_refs,
        "v218_ref_count": v218_refs,
        "wired": wired,
        "disposition": "WIRED_REQUIRES_RUNTIME_GATE" if wired else "BLOCKED_AT_NATIVE_ASSEMBLY",
        "scope": "binding/custody only; no V218 execution or economics",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("native", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--require-wired", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = audit(args.native)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        ap.exit(2, f"v218-native-binding: {exc}\n")
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.require_wired and not report["wired"]:
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
