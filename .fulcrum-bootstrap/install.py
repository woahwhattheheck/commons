# SPDX-License-Identifier: Apache-2.0
"""Verify and unpack the exact SOL-FULCRUM authored tree."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path, PurePosixPath
import tarfile

ARCHIVE_SHA256 = "6da543016a655774c4b6bd53854461d82dfa11b8c3cfc1c92e9b4d8a48b9d5d0"
PATHS_SHA256 = "aee944f9464034f0d0c9ed645fc915ce1c4ed07915df5ca2930114238732d11e"
EXPECTED_FILES = 26
EXPECTED_PARTS = 44
ROOT = Path(".fulcrum-bootstrap")

parts = sorted(ROOT.glob("part-*.b64"))
expected_parts = [f"part-{index:03d}.b64" for index in range(EXPECTED_PARTS)]
if [part.name for part in parts] != expected_parts:
    raise SystemExit("transport chunk inventory mismatch")
encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
payload = base64.b64decode(encoded, validate=True)
actual_sha = hashlib.sha256(payload).hexdigest()
if actual_sha != ARCHIVE_SHA256:
    raise SystemExit(f"archive sha256 mismatch: {actual_sha}")
with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
    members = archive.getmembers()
    names = sorted(member.name for member in members)
    names_payload = ("\n".join(names) + "\n").encode("utf-8")
    if len(members) != EXPECTED_FILES or len(set(names)) != EXPECTED_FILES:
        raise SystemExit("archive path count mismatch")
    if hashlib.sha256(names_payload).hexdigest() != PATHS_SHA256:
        raise SystemExit("archive path inventory mismatch")
    for member in members:
        path = PurePosixPath(member.name)
        if not member.isfile() or path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"unsafe archive member: {member.name}")
    archive.extractall(".", members=members)
print(f"unpacked {EXPECTED_FILES} exact files from {EXPECTED_PARTS} chunks")
