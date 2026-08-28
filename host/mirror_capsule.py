# mirror_capsule.py — portable content-addressed Commons snapshot
# A bake is not the board. Reachable is not canonical.
from __future__ import annotations
import hashlib, io, json, posixpath, re, tarfile, subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "commons-mirror-capsule-v1"
ENVELOPE_SCHEMA = "commons-envelope-v1"
QUEUE_SCHEMA = "commons-capsule-writeback-queue-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
CLAIM_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
DEFAULT_SELECTION = ("START.md", "ENTRY.md", "CRAWLERS.md", "ISSUE.md", "mirrors.json", "mirror.html", "ground/HEAD.md", "ground/OPEN_DOOR.md", "ground/EXECUTE.md", "ground/LAND.md", "relay-manifest.schema.json")
CLAIM_BOUNDARY = {"portable_snapshot": True, "canonical": False, "moving_main_sync": False, "provider_writeback": False, "independent_origin": False, "canonical_durability": False, "live_hosting": False, "reachable_is_not_canonical": True}

class CapsuleError(ValueError):
    pass
class PathRejected(CapsuleError):
    pass
class HashCorrupt(CapsuleError):
    pass
class AmbiguousSource(CapsuleError):
    pass

def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()

def canonical_json(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

def media_type(path):
    return {".md": "text/markdown; charset=utf-8", ".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".txt": "text/plain; charset=utf-8"}.get(posixpath.splitext(path)[1].lower(), "application/octet-stream")

def normalize_path(raw):
    if raw is None:
        raise PathRejected("empty path")
    text = str(raw).replace("\\", "/")
    if "\\" in str(raw) or text.startswith(("/", "./", "../", "~")) or re.match(r"^[A-Za-z]:", text) or "//" in text or text.endswith("/") or text in ("", "."):
        raise PathRejected("illegal path: %s" % raw)
    parts = text.split("/")
    if any(part in ("", ".", "..") or part.startswith(".git") for part in parts) or posixpath.normpath(text) != text:
        raise PathRejected("traversal or git path: %s" % raw)
    return text

def _resolve_source_sha(root, source_sha):
    if source_sha:
        sha = source_sha.strip().lower()
        if not COMMIT_RE.match(sha):
            raise AmbiguousSource("source SHA must be 40 hex chars")
        return sha
    if not (Path(root) / ".git").exists():
        raise AmbiguousSource("no source SHA and no git directory")
    probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    sha = probe.stdout.strip().lower()
    if probe.returncode != 0 or not COMMIT_RE.match(sha):
        raise AmbiguousSource("git HEAD is not a 40-hex commit")
    return sha

def _read_regular_file(root, rel):
    path = Path(root).joinpath(*rel.split("/"))
    if path.is_symlink() or not path.is_file():
        raise PathRejected("not a regular file: %s" % rel)
    try:
        path.resolve().relative_to(Path(root).resolve())
    except ValueError as exc:
        raise PathRejected("escaped root: %s" % rel) from exc
    return path.read_bytes()
