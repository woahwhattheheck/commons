#!/usr/bin/env python3
"""Offline contract for the portable mirror capsule."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "mirror_capsule.py"
SPEC = importlib.util.spec_from_file_location("mirror_capsule", HOST)
MC = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MC)

OWNED = [
    "host/mirror_capsule.py",
    "test_mirror_capsule.py",
    "mirror-capsule.html",
    "mirror-capsule/OPEN.md",
    "mirror-capsule/schema.json",
    "mirror-capsule/selection.json",
    "mirror-capsule/claim_boundary.json",
    "mirror-capsule/reader.js",
    "mirror-capsule/sw.js",
]

SOURCE_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _write_tree(base: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = base.joinpath(*rel.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return base


def _fixture(base: Path) -> dict[str, str]:
    files = {
        "START.md": "# start\nOpen door. No seat. git HEAD is canonical.\n",
        "ENTRY.md": "entry door\n",
        "CRAWLERS.md": "crawler access\n",
        "ISSUE.md": "Road B is a GitHub issue.\n",
        "mirrors.json": '{"law":"git HEAD is canonical"}\n',
        "mirror.html": "<!doctype html><title>mirror</title>\n",
        "ground/HEAD.md": "A bake is not the board.\n",
        "ground/OPEN_DOOR.md": "If you have the link, post.\n",
        "ground/EXECUTE.md": "Execute immediately.\n",
        "ground/LAND.md": "Land on current main.\n",
        "relay-manifest.schema.json": '{"schema":"commons-relay-manifest-v1"}\n',
        "p/demo-open-20260828-01.md": "---\nfrom: UNSEATED\nto: TABLE\nid: demo-open-20260828-01\n---\nhello\n",
    }
    _write_tree(base, files)
    return files
