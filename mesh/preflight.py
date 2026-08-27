#!/usr/bin/env python3
"""KITE-178 content-addressed preflight. No push."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PATHS = [
    "mesh/PROTOCOL-v1.md",
    "mesh/core.py",
    "mesh/__init__.py",
    "mesh/package.json",
    "mesh/.gitignore",
    "mesh/nodes.json",
    "mesh/cursors.json",
    "mesh/reachability.json",
    "mesh/reachability.html",
    "mesh/canonical-manifest.json",
    "mesh/schemas/envelope-v1.json",
    "mesh/schemas/receipt-v1.json",
    "mesh/worker/src/index.mjs",
    "mesh/worker/src/protocol.mjs",
    "mesh/worker/schema.sql",
    "mesh/worker/wrangler.toml.example",
    "mesh/worker/public/index.html",
    "mesh/worker/public/robots.txt",
    "mesh/tests/mesh.test.mjs",
    "mesh/d/README.md",
    "mesh/preflight.py",
    "ground/mirror_mesh.py",
    "ground/MIRROR_MESH_0.md",
    "board_ingest.py",
    "board.js",
    "hub_pages.py",
    "ENTRY.md",
    "carrier.js",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e:
        return "ERR %s" % e


head = git("rev-parse", "HEAD")
branch = git("rev-parse", "--abbrev-ref", "HEAD")
print("base_HEAD", head)
print("working_branch", branch)
print("intended_target origin/main (NO PUSH this tranche)")
print("node_suite NOT_RUN (node binary absent on this PATH)")
print("--- manifest ---")
rows = []
for rel in PATHS:
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        print("MISSING", rel)
        continue
    n = os.path.getsize(p)
    s = sha256(p)
    rows.append((rel, n, s))
    print("%s\t%d\t%s" % (rel, n, s))
print("n_files", len(rows))
sys.exit(0)
