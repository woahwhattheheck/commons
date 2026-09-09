# SPDX-License-Identifier: Apache-2.0
"""Verify and unpack the exact SOL-FULCRUM authored tree."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path, PurePosixPath
import tarfile

ARCHIVE_SHA256 = "e5c568bad7cf2c315c19fa49f6b99571e7b4e52a1e90aac6e723c4b07512ada5"
ROOT = Path(".fulcrum-bootstrap")

parts = sorted(ROOT.glob("part-*.b64"))
expected_parts = [f"part-{index:03d}.b64" for index in range(14)]
if [part.name for part in parts] != expected_parts:
    raise SystemExit("transport chunk inventory mismatch")
encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
payload = base64.b64decode(encoded, validate=True)
actual_sha = hashlib.sha256(payload).hexdigest()
if actual_sha != ARCHIVE_SHA256:
    raise SystemExit(f"archive sha256 mismatch: {actual_sha}")
expected = set((ROOT / "manifest.txt").read_text(encoding="utf-8").splitlines())
if not expected or "" in expected:
    raise SystemExit("empty transport manifest")
with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
    members = archive.getmembers()
    if {member.name for member in members} != expected or len(members) != len(expected):
        raise SystemExit("archive path inventory mismatch")
    for member in members:
        path = PurePosixPath(member.name)
        if not member.isfile() or path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"unsafe archive member: {member.name}")
    archive.extractall(".", members=members)
print(f"unpacked {len(expected)} exact files from {len(parts)} chunks")
