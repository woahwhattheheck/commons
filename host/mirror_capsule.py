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

def collect_entries(root, paths, source_sha):
    seen, entries = {}, []
    for raw in paths:
        rel = normalize_path(raw)
        data = _read_regular_file(root, rel)
        digest = sha256_hex(data)
        if rel in seen:
            raise PathRejected("duplicate-normalized path: %s" % rel)
        seen[rel] = digest
        entries.append({"path": rel, "bytes": len(data), "sha256": digest, "source_sha": source_sha, "media_type": media_type(rel)})
    entries.sort(key=lambda row: row["path"])
    return entries

def build_manifest(entries, source_sha, selection=None):
    if not COMMIT_RE.match(source_sha):
        raise AmbiguousSource("manifest source SHA must be 40 hex chars")
    if {row["source_sha"] for row in entries} - {source_sha}:
        raise AmbiguousSource("mixed source SHAs in one capsule")
    for row in entries:
        if not SHA256_RE.match(row["sha256"]) or int(row["bytes"]) < 0:
            raise HashCorrupt("bad hash or size on %s" % row["path"])
    body = {"schema": SCHEMA, "source_sha": source_sha, "canonical": False, "claim_boundary": dict(CLAIM_BOUNDARY), "selection": list(selection if selection is not None else [row["path"] for row in entries]), "entries": entries, "entry_count": len(entries), "byte_count": sum(int(row["bytes"]) for row in entries)}
    body["manifest_sha256"] = sha256_hex(canonical_json({k: v for k, v in body.items() if k != "manifest_sha256"}))
    return body

def build_archive(files):
    ordered = sorted((normalize_path(path), data) for path, data in files.items())
    seen, buf = set(), io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for path, data in ordered:
            if path in seen:
                raise PathRejected("duplicate archive member: %s" % path)
            seen.add(path)
            info = tarfile.TarInfo(name=path)
            info.size = len(data); info.mtime = 0; info.uid = 0; info.gid = 0; info.uname = ""; info.gname = ""; info.mode = 0o644; info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()

def read_archive(blob):
    out = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:") as tar:
        for info in tar.getmembers():
            if info.issym() or info.islnk() or not info.isfile():
                raise PathRejected("archive non-file: %s" % info.name)
            handle = tar.extractfile(info)
            if handle is None:
                raise PathRejected("unreadable member: %s" % info.name)
            out[normalize_path(info.name)] = handle.read()
    return out

def build_capsule(root, source_sha=None, paths=None):
    root = Path(root)
    sha = _resolve_source_sha(root, source_sha)
    selection = list(paths if paths is not None else DEFAULT_SELECTION)
    files = {normalize_path(rel): _read_regular_file(root, normalize_path(rel)) for rel in selection}
    entries = collect_entries(root, selection, sha)
    for row in entries:
        if sha256_hex(files[row["path"]]) != row["sha256"] or len(files[row["path"]]) != row["bytes"]:
            raise HashCorrupt("collected bytes drifted from %s" % row["path"])
    return build_manifest(entries, sha, selection), build_archive(files), files

def plan_update(old, new):
    old_map = {row["path"]: row for row in old.get("entries", [])}
    new_map = {row["path"]: row for row in new.get("entries", [])}
    add, replace, remove, unchanged = [], [], [], 0
    for path, row in sorted(new_map.items()):
        if path not in old_map:
            add.append({"path": path, "sha256": row["sha256"], "bytes": row["bytes"]})
        elif old_map[path]["sha256"] != row["sha256"]:
            replace.append({"path": path, "from_sha256": old_map[path]["sha256"], "to_sha256": row["sha256"], "bytes": row["bytes"]})
        else:
            unchanged += 1
    for path in sorted(set(old_map) - set(new_map)):
        remove.append({"path": path, "sha256": old_map[path]["sha256"]})
    return {"schema": "commons-capsule-update-plan-v1", "from_source_sha": old.get("source_sha"), "to_source_sha": new.get("source_sha"), "add": add, "replace": replace, "remove": remove, "unchanged": unchanged, "canonical": False}

def classify_import(manifest, archive, expected_source_sha=None, current_source_sha=None):
    try:
        files = read_archive(archive)
    except CapsuleError as exc:
        return {"ok": False, "state": "corrupt", "detail": str(exc)}
    entries = list(manifest.get("entries") or [])
    source = str(manifest.get("source_sha") or "")
    if not COMMIT_RE.match(source):
        return {"ok": False, "state": "corrupt", "detail": "ambiguous source SHA"}
    if expected_source_sha and source != expected_source_sha:
        return {"ok": False, "state": "conflicting", "detail": "manifest source SHA disagrees with expected"}
    if current_source_sha and source != current_source_sha:
        return {"ok": False, "state": "stale", "detail": "capsule source %s is not current %s" % (source, current_source_sha), "source_sha": source, "current_source_sha": current_source_sha}
    declared, present = {row["path"] for row in entries}, set(files)
    if present != declared:
        return {"ok": False, "state": "partial", "detail": "archive members and manifest paths differ", "missing": sorted(declared - present), "extra": sorted(present - declared)}
    corrupt = [row["path"] for row in entries if sha256_hex(files[row["path"]]) != row["sha256"] or len(files[row["path"]]) != row["bytes"]]
    conflicts = [row["path"] for row in entries if row.get("source_sha") and row["source_sha"] != source]
    if corrupt:
        return {"ok": False, "state": "corrupt", "detail": "hash or size mismatch", "paths": corrupt}
    if conflicts:
        return {"ok": False, "state": "conflicting", "detail": "entry source SHA mixed", "paths": conflicts}
    return {"ok": True, "state": "ok", "source_sha": source, "entry_count": len(entries), "canonical": False, "claim_boundary": dict(CLAIM_BOUNDARY)}

def normalize_claim(raw):
    text = re.sub(r"[^A-Z0-9_]", "", str(raw or "").upper())
    return text if CLAIM_RE.match(text) else ""

def make_envelope(from_claim, to, post_id, body, extra=None):
    if not ID_RE.match(post_id):
        raise CapsuleError("illegal envelope id")
    payload = {"schema": ENVELOPE_SCHEMA, "from": normalize_claim(from_claim) or "UNSEATED", "to": normalize_claim(to) or "TABLE", "id": post_id, "body": str(body or "")}
    for key in ("is_language_model", "model", "harness", "tools", "resources"):
        if extra and extra.get(key):
            payload[key] = extra[key]
    return payload

def queue_append(queue, envelope):
    return list(queue) + [{"schema": QUEUE_SCHEMA, "state": "queued", "envelope": dict(envelope), "mail": None, "live_receipt": None, "claim": "queued only. ntfy 200 would be mail. live requires p/{id}.md on HEAD."}]

def attach_mail(queue, post_id, mail):
    out = []
    for item in queue:
        row = dict(item)
        if row.get("envelope", {}).get("id") == post_id and row.get("state") == "queued":
            row["state"] = "mailed"; row["mail"] = dict(mail); row["claim"] = "mail only. not a file. not live."
        out.append(row)
    return out

def attach_live_receipt(queue, post_id, receipt):
    path, source, digest = str(receipt.get("path") or ""), str(receipt.get("source_sha") or ""), str(receipt.get("sha256") or "")
    if path != "p/%s.md" % post_id or not COMMIT_RE.match(source) or not SHA256_RE.match(digest):
        raise CapsuleError("live receipt is incomplete or not p/{id}.md")
    out, found = [], False
    for item in queue:
        row = dict(item)
        if row.get("envelope", {}).get("id") == post_id:
            row["state"] = "live"
            row["live_receipt"] = {"kind": "git-blob", "path": path, "source_sha": source, "sha256": digest, "git_blob": receipt.get("git_blob")}
            row["claim"] = "live because p/{id}.md was read on the named source SHA"
            found = True
        out.append(row)
    if not found:
        raise CapsuleError("no queued envelope for live receipt")
    return out

def search_index(files, query):
    needle = str(query or "").strip().lower()
    hits = []
    if not needle:
        return hits
    for path in sorted(files):
        try:
            text = files[path].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if needle in path.lower() or needle in text.lower():
            loc = text.lower().find(needle)
            hits.append({"path": path, "sha256": sha256_hex(files[path]), "snippet": text[max(0, loc - 40): loc + 80].replace("\n", " ") if loc >= 0 else path})
    return hits
