#!/usr/bin/env python3
"""Automatic moving-main read copies, independent-origin durability, bounded writeback.

Composes with host/repo_backup.py and host/mirror_capsule.py. Does not remint
read_mesh.py, head.js, slack_mirror.py, or the jsDelivr receipts already on
main. A bake is not the board. ntfy 200 is mail. Canonical durability remains
p/{id}.md on git HEAD.

Zero-new-credential automatic roads (GitHub Actions or already-public
endpoints): ntfy cursor topic, jsDelivr @main compose, Software Heritage
save-code-now. Internet Archive SavePageNow is attempted and reported exactly.
GitLab / Codeberg / object-store full-bundle copies stay
EXTERNAL_PROVIDER_ACTION until an origin URL exists outside this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import repo_backup

SCHEMA_VERSION = "commons-moving-main-mirror/v1"
CURSOR_KIND = "commons-main-cursor"
CURSOR_TOPIC = "woahwhattheheck-commons-main"
WRITE_TOPIC = "woahwhattheheck-commons-board"
FRESH_TOPIC = "woahwhattheheck-commons-fresh"
MAX_BYTES = 3900
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SECRET_RE = re.compile(
    r"(?i)(authorization|token|secret|password|api[_-]?key|bearer)\s*[:=]\s*\S+"
)
NTFY_HOSTS = (
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
)
DEFAULT_PATHS = (
    "fresh.md",
    "mirrors.json",
    "ground/HEAD.md",
    "ground/BACKUP_OPEN_REPO.md",
    "ground/MOVING_MAIN_MIRROR.md",
    "START.md",
    "ENTRY.md",
)
SWH_SAVE = (
    "https://archive.softwareheritage.org/api/1/origin/save/git/url/"
    "https://github.com/woahwhattheheck/commons/"
)
SWH_ORIGIN = (
    "https://archive.softwareheritage.org/api/1/origin/"
    "https://github.com/woahwhattheheck/commons/get/"
)
IA_SAVE_PREFIX = "https://web.archive.org/save/"
PAGES = "https://woahwhattheheck.github.io/commons/"
JSDELIVR_MAIN = "https://cdn.jsdelivr.net/gh/woahwhattheheck/commons@main/"
USER_AGENT = "commons-moving-main-mirror/1.0 (+https://github.com/woahwhattheheck/commons)"


class MirrorError(RuntimeError):
    """A snapshot, cursor, adapter, or restore failed its measured contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact(text: Any) -> str:
    return SECRET_RE.sub(r"\1=<redacted>", str(text or ""))


def refuse_write_topic(url: str) -> bool:
    return WRITE_TOPIC in str(url or "")


def refuse_fresh_topic(url: str) -> bool:
    return FRESH_TOPIC in str(url or "")


def canonical_json(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _git(root: Path, *args: str, check: bool = True) -> str:
    import subprocess

    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode:
        raise MirrorError(redact(completed.stderr.strip() or completed.stdout.strip() or args))
    return completed.stdout.strip()


def relation(root: Path, older: str, newer: str) -> str:
    if not older or older == newer:
        return "equal" if older == newer else "ancestor"
    if subprocess_ok(root, "merge-base", "--is-ancestor", older, newer):
        return "ancestor"
    if subprocess_ok(root, "merge-base", "--is-ancestor", newer, older):
        return "descendant"
    return "diverged"


def subprocess_ok(root: Path, *args: str) -> bool:
    import subprocess

    return (
        subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def head_sha(root: Path) -> str:
    sha = _git(root, "rev-parse", "HEAD").lower()
    if not SHA_RE.fullmatch(sha):
        raise MirrorError("HEAD is not a full object id")
    return sha


def read_paths(root: Path, paths: Iterable[str], sha: str | None = None) -> list[dict[str, Any]]:
    rows = []
    for rel in paths:
        rel = str(rel).replace("\\", "/").lstrip("./")
        if not rel or ".." in rel.split("/") or rel.startswith("/"):
            raise MirrorError("illegal path")
        if sha:
            data = _git(root, "show", f"{sha}:{rel}", check=True).encode("utf-8") if False else _show_bytes(root, sha, rel)
        else:
            path = root / rel
            if not path.is_file():
                continue
            data = path.read_bytes()
        rows.append({"path": rel, "bytes": len(data), "sha256": sha256_hex(data)})
    if not rows:
        raise MirrorError("snapshot has no readable paths")
    return rows


def _show_bytes(root: Path, sha: str, rel: str) -> bytes:
    import subprocess

    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{sha}:{rel}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise MirrorError(f"missing {rel} at {sha}")
    return completed.stdout


def build_snapshot(root: Path, paths: Iterable[str] | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    sha = head_sha(root)
    selected = list(paths or DEFAULT_PATHS)
    entries = []
    for rel in selected:
        try:
            data = _show_bytes(root, sha, rel)
        except MirrorError:
            continue
        entries.append({"path": rel, "bytes": len(data), "sha256": sha256_hex(data)})
    if not entries:
        raise MirrorError("snapshot has no git blobs")
    body = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "head_sha": sha,
        "entries": entries,
    }
    body["digest"] = sha256_hex(canonical_json({k: body[k] for k in ("head_sha", "entries")}))
    return body


def merge_manifests(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    left_map = {row["path"]: row for row in left.get("entries") or []}
    right_map = {row["path"]: row for row in right.get("entries") or []}
    if len(left_map) != len(left.get("entries") or []) or len(right_map) != len(right.get("entries") or []):
        raise MirrorError("duplicate paths while merging")
    merged: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    identical = 0
    disjoint = 0
    for path in sorted(set(left_map) | set(right_map)):
        a, b = left_map.get(path), right_map.get(path)
        if a and not b:
            merged[path] = dict(a)
            disjoint += 1
        elif b and not a:
            merged[path] = dict(b)
            disjoint += 1
        elif a["sha256"] == b["sha256"] and a["bytes"] == b["bytes"]:
            merged[path] = dict(a)
            identical += 1
        else:
            conflicts.append(
                {
                    "path": path,
                    "left": a["sha256"],
                    "right": b["sha256"],
                }
            )
    state = "CONFLICT" if conflicts else "MERGED"
    return {
        "state": state,
        "identical": identical,
        "disjoint": disjoint,
        "conflicts": conflicts,
        "entries": [merged[path] for path in sorted(merged)],
        "heads": [left.get("head_sha"), right.get("head_sha")],
    }


def advance_cursor(
    previous: Mapping[str, Any] | None,
    snapshot: Mapping[str, Any],
    rel: str,
) -> dict[str, Any]:
    seq = int((previous or {}).get("seq") or 0)
    digest = str(snapshot["digest"])
    head = str(snapshot["head_sha"])
    if previous:
        prev_head = str(previous.get("head_sha") or "")
        prev_digest = str(previous.get("digest") or "")
        if prev_head == head and prev_digest == digest:
            return {
                "state": "IDEMPOTENT",
                "seq": seq,
                "head_sha": head,
                "digest": digest,
                "action": "no-second-publish",
            }
        if rel == "descendant":
            return {
                "state": "STALE",
                "seq": seq,
                "head_sha": prev_head,
                "digest": prev_digest,
                "incoming_head": head,
                "note": "refusing to walk main backwards",
            }
        if rel == "diverged":
            merged = merge_manifests(previous, snapshot)
            if merged["state"] == "CONFLICT":
                return {
                    "state": "CONFLICT",
                    "seq": seq,
                    "head_sha": prev_head,
                    "digest": prev_digest,
                    "incoming_head": head,
                    "conflicts": merged["conflicts"],
                    "note": "same-path disagreement; not last-write-wins",
                }
            seq += 1
            return {
                "state": "OVERLAP_MERGED",
                "seq": seq,
                "head_sha": head,
                "digest": digest,
                "identical": merged["identical"],
                "disjoint": merged["disjoint"],
            }
        if rel not in {"ancestor", "equal"}:
            raise MirrorError(f"unknown relation {rel}")
        if rel == "equal" and prev_digest != digest:
            return {
                "state": "CORRUPT",
                "seq": seq,
                "head_sha": head,
                "note": "same SHA, different digest",
            }
    seq += 1
    return {
        "state": "ADVANCE",
        "seq": seq,
        "head_sha": head,
        "digest": digest,
    }


def compact_cursor(snapshot: Mapping[str, Any], cursor: Mapping[str, Any]) -> bytes:
    newest = []
    for row in snapshot.get("entries") or []:
        newest.append(
            {
                "p": row["path"],
                "n": int(row["bytes"]),
                "h": str(row["sha256"])[:16],
            }
        )
    payload = {
        "kind": CURSOR_KIND,
        "schema": SCHEMA_VERSION,
        "seq": int(cursor["seq"]),
        "head": str(cursor["head_sha"])[:40],
        "ts": str(snapshot.get("created_at") or utc_now()),
        "digest": str(cursor["digest"])[:32],
        "state": str(cursor.get("state") or "ADVANCE"),
        "paths": newest,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    while len(raw) > MAX_BYTES and payload["paths"]:
        payload["paths"].pop()
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_BYTES:
        payload["paths"] = []
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return raw


def detect_corrupt(snapshot: Mapping[str, Any], blobs: Mapping[str, bytes]) -> list[str]:
    bad = []
    for row in snapshot.get("entries") or []:
        data = blobs.get(row["path"])
        if data is None:
            bad.append(row["path"])
            continue
        if sha256_hex(data) != row["sha256"] or len(data) != row["bytes"]:
            bad.append(row["path"])
    return bad


def prefer_receipts(receipts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in receipts if isinstance(row, dict)]
    verified = [row for row in rows if row.get("verified")]
    independent = [row for row in verified if row.get("independent_origin")]
    pool = independent or verified or rows
    if not pool:
        return {"state": "EMPTY", "receipts": []}
    keys = []
    for row in pool:
        key = str(row.get("head_sha") or row.get("digest") or row.get("sha256") or "")
        keys.append(key)
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row, key in zip(pool, keys):
        by_key.setdefault(key, []).append(row)
    if len(by_key) > 1:
        return {
            "state": "CONFLICT",
            "note": "independently verified receipts disagree",
            "receipts": pool,
        }
    chosen = sorted(
        pool,
        key=lambda row: (
            0 if row.get("independent_origin") else 1,
            0 if row.get("verified") else 1,
            str(row.get("id") or ""),
        ),
    )
    return {
        "state": "PREFERRED",
        "receipt": chosen[0],
        "agreeing": len(pool),
        "independent": len(independent),
        "receipts": chosen,
    }


ADAPTERS = (
    {
        "id": "ntfy-cursor",
        "kind": "automatic-moving-main-cursor",
        "credentials": "none",
        "independent_origin": True,
        "operational": True,
        "href": "https://ntfy.sh/" + CURSOR_TOPIC,
        "notes": "Public ntfy topic. GitHub Actions POSTs the compact HEAD cursor with no new secret. Retention is hours, not corpus.",
        "external_provider_action": None,
    },
    {
        "id": "jsdelivr-main",
        "kind": "automatic-non-github-moving-main-read",
        "credentials": "none",
        "independent_origin": False,
        "operational": True,
        "href": JSDELIVR_MAIN + "fresh.md",
        "notes": "Already landed. head.js fallback. GitHub-backed CDN. Compose, do not remint.",
        "external_provider_action": None,
    },
    {
        "id": "software-heritage",
        "kind": "independent-origin-git-save",
        "credentials": "none",
        "independent_origin": True,
        "operational": True,
        "href": SWH_SAVE,
        "notes": "Zero-new-credential Save Code Now from GitHub Actions. Origin-readable after the visit finishes. Not canonical durability.",
        "external_provider_action": None,
    },
    {
        "id": "internet-archive",
        "kind": "independent-origin-web-save",
        "credentials": "none",
        "independent_origin": True,
        "operational": False,
        "href": IA_SAVE_PREFIX + PAGES + "mirrors.json",
        "notes": "Repo-controlled SavePageNow adapter. Last measured HTTP 523 from Wayback. Status stays exact; not READY.",
        "external_provider_action": None,
    },
    {
        "id": "actions-bundle-artifact",
        "kind": "same-forge-bundle-artifact",
        "credentials": "none",
        "independent_origin": False,
        "operational": True,
        "href": "./.github/workflows/open-repo-backup.yml",
        "notes": "Already landed. Daily host/repo_backup.py restore drill uploads commons-open-repo-backup (90-day artifact). Same forge, not GitHub-outage protection. Compose, do not remint.",
        "external_provider_action": None,
    },
    {
        "id": "ntfy-writeback",
        "kind": "bounded-writeback",
        "credentials": "none",
        "independent_origin": True,
        "operational": True,
        "href": "https://ntfy.sh/" + WRITE_TOPIC,
        "notes": "Existing ntfy write road, size-capped, id+hash idempotent. Same id different hash is CONFLICT. Never last-write-wins. Never overwrites p/{id}.md.",
        "external_provider_action": None,
    },
    {
        "id": "gitlab-pull-mirror",
        "kind": "independent-origin-git-forge",
        "credentials": "EXTERNAL_PROVIDER_ACTION",
        "independent_origin": True,
        "operational": False,
        "href": None,
        "notes": "Repo-controlled adapter is dark until a public GitLab origin exists.",
        "external_provider_action": (
            "On GitLab.com, create a public project whose pull-mirror origin is "
            "https://github.com/woahwhattheheck/commons.git. Do not put a token in this "
            "repository. After the public project URL exists, set adapter "
            "gitlab-pull-mirror.origin to that URL so the courier can read it back."
        ),
    },
    {
        "id": "codeberg-pull-mirror",
        "kind": "independent-origin-git-forge",
        "credentials": "EXTERNAL_PROVIDER_ACTION",
        "independent_origin": True,
        "operational": False,
        "href": None,
        "notes": "Repo-controlled adapter is dark until a public Codeberg origin exists.",
        "external_provider_action": (
            "On Codeberg, create a public repository that pull-mirrors "
            "https://github.com/woahwhattheheck/commons.git. Do not put a token in this "
            "repository. After the public origin URL exists, set adapter "
            "codeberg-pull-mirror.origin to that URL."
        ),
    },
    {
        "id": "object-store-bundle",
        "kind": "independent-origin-bundle",
        "credentials": "EXTERNAL_PROVIDER_ACTION",
        "independent_origin": True,
        "operational": False,
        "href": None,
        "notes": "Full git-bundle durability outside GitHub. Adapter writes only after a public bucket/origin is named.",
        "external_provider_action": (
            "Provision a public-read object prefix (R2, S3, or equivalent) that can store "
            "the sibling .bundle and .manifest.json from host/repo_backup.py. Do not put "
            "access keys in this repository. After a public HTTPS origin exists, set "
            "adapter object-store-bundle.origin to that prefix."
        ),
    },
)


def adapters_catalog() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ts": "2026-08-28T15:30:00Z",
        "law": "git HEAD is canonical. Mirrors copy and can post back. A receipt is not the board.",
        "compose": [
            "host/repo_backup.py",
            ".github/workflows/open-repo-backup.yml",
            "host/mirror_capsule.py",
            "read_mesh.py",
            "head.js",
            "host/slack_mirror.py",
        ],
        "adapters": list(ADAPTERS),
        "still_open": (
            "GitLab/Codeberg/object-store full-bundle independent origins remain "
            "EXTERNAL_PROVIDER_ACTION. Internet Archive SavePageNow last measured HTTP 523. "
            "jsDelivr is GitHub-backed. None of these is canonical durability."
        ),
    }


def http_call(
    url: str,
    data: bytes | None = None,
    method: str | None = None,
    timeout: int = 20,
    post: Callable[..., int] | None = None,
) -> dict[str, Any]:
    if post is not None and data is not None:
        status = post(url, data)
        return {"url": url, "status": int(status), "body": b"", "headers": {}}
    verb = method or ("POST" if data is not None else "GET")
    req = urllib.request.Request(
        url,
        data=data,
        method=verb,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8" if data is not None else "text/plain",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "url": url,
                "status": int(getattr(resp, "status", 200) or 200),
                "body": body,
                "headers": headers,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return {
            "url": url,
            "status": int(exc.code),
            "body": body,
            "headers": {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])},
            "error": redact(exc),
        }
    except Exception as exc:  # noqa: BLE001 — transport miss is a measured state
        return {"url": url, "status": 0, "body": b"", "headers": {}, "error": redact(exc)}


def publish_ntfy_cursor(payload: bytes, post: Callable[..., int] | None = None) -> dict[str, Any]:
    last = "no host"
    for host in NTFY_HOSTS:
        url = f"{host}/{CURSOR_TOPIC}"
        if refuse_write_topic(url) or refuse_fresh_topic(url):
            last = "refused other topic"
            continue
        result = http_call(url, data=payload, post=post)
        if result["status"] == 200:
            return {
                "id": "ntfy-cursor",
                "state": "PUBLISHED",
                "url": url,
                "status": 200,
                "verified": True,
                "independent_origin": True,
                "digest": sha256_hex(payload),
            }
        last = f"http {result['status']}"
    return {"id": "ntfy-cursor", "state": "MISS", "note": last, "verified": False}


def readback_ntfy_cursor(expected_digest: str | None = None) -> dict[str, Any]:
    url = f"https://ntfy.sh/{CURSOR_TOPIC}/json?poll=1&since=24h"
    if refuse_write_topic(url) or refuse_fresh_topic(url):
        raise MirrorError("refusing to read a different ntfy topic")
    result = http_call(url)
    text = result["body"].decode("utf-8", "replace")
    found = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = row.get("message")
        if not message:
            continue
        try:
            msg = json.loads(message) if isinstance(message, str) else message
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and msg.get("kind") == CURSOR_KIND:
            found.append(msg)
    if not found:
        return {"id": "ntfy-cursor", "state": "MISS", "verified": False, "url": url}
    last = found[-1]
    blob = json.dumps(last, separators=(",", ":")).encode("utf-8")
    digest = sha256_hex(blob)
    verified = True if expected_digest is None else expected_digest.startswith(str(last.get("digest") or ""))
    return {
        "id": "ntfy-cursor",
        "state": "READBACK",
        "verified": bool(verified),
        "independent_origin": True,
        "head": last.get("head"),
        "seq": last.get("seq"),
        "digest": digest,
        "url": url,
        "cursor": last,
    }


def publish_software_heritage() -> dict[str, Any]:
    result = http_call(SWH_SAVE, data=b"", method="POST", timeout=40)
    body = {}
    try:
        body = json.loads(result["body"].decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}
    accepted = result["status"] in {200, 201} and str(body.get("save_request_status") or "") in {
        "accepted",
        "pending",
    }
    return {
        "id": "software-heritage",
        "state": "SAVE_ACCEPTED" if accepted else "MISS",
        "verified": bool(accepted),
        "independent_origin": True,
        "status": result["status"],
        "save_id": body.get("id"),
        "save_request_status": body.get("save_request_status"),
        "save_task_status": body.get("save_task_status"),
        "visit_status": body.get("visit_status"),
        "request_url": body.get("request_url"),
        "origin_url": body.get("origin_url") or "https://github.com/woahwhattheheck/commons",
        "note": "origin becomes readable after the visit finishes; snapshot_swhid may still be null",
    }


def readback_software_heritage(request_url: str | None = None) -> dict[str, Any]:
    url = request_url or SWH_ORIGIN
    result = http_call(url, timeout=30)
    body = {}
    try:
        body = json.loads(result["body"].decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}
    if result["status"] == 200 and body:
        return {
            "id": "software-heritage",
            "state": "READBACK",
            "verified": True,
            "independent_origin": True,
            "status": 200,
            "url": url,
            "body_keys": sorted(body),
            "save_task_status": body.get("save_task_status"),
            "visit_status": body.get("visit_status"),
            "snapshot_swhid": body.get("snapshot_swhid"),
        }
    return {
        "id": "software-heritage",
        "state": "PENDING" if result["status"] in {404, 200} else "MISS",
        "verified": False,
        "independent_origin": True,
        "status": result["status"],
        "url": url,
        "note": redact(result.get("error") or body.get("reason") or "origin not yet listed"),
    }


def publish_internet_archive(path: str = "mirrors.json") -> dict[str, Any]:
    url = IA_SAVE_PREFIX + PAGES + path.lstrip("/")
    result = http_call(url, timeout=40)
    ok = result["status"] in {200, 201, 302}
    return {
        "id": "internet-archive",
        "state": "PUBLISHED" if ok else "MISS",
        "verified": bool(ok),
        "independent_origin": True,
        "status": result["status"],
        "url": url,
        "final": result.get("headers", {}).get("content-location") or result.get("headers", {}).get("location"),
        "note": None if ok else f"SavePageNow HTTP {result['status']}; not READY",
    }


def publish_jsdelivr_readback(path: str = "fresh.md") -> dict[str, Any]:
    url = JSDELIVR_MAIN + path.lstrip("/")
    result = http_call(url, timeout=20)
    body = result["body"]
    headers = result.get("headers") or {}
    ok = result["status"] == 200 and body
    return {
        "id": "jsdelivr-main",
        "state": "READBACK" if ok else "MISS",
        "verified": bool(ok),
        "independent_origin": False,
        "status": result["status"],
        "url": url,
        "bytes": len(body),
        "sha256": sha256_hex(body) if body else None,
        "x-jsd-version": headers.get("x-jsd-version"),
        "x-jsd-version-type": headers.get("x-jsd-version-type"),
        "note": "GitHub-backed CDN compose; not independent origin",
    }


def bounded_writeback(envelope: Mapping[str, Any], post: Callable[..., int] | None = None) -> dict[str, Any]:
    post_id = str(envelope.get("id") or "")
    body = str(envelope.get("body") or "")
    if not post_id or not body.strip():
        raise MirrorError("writeback envelope needs id and body")
    payload = json.dumps(
        {
            "from": str(envelope.get("from") or "UNSEATED"),
            "to": str(envelope.get("to") or "TABLE"),
            "id": post_id,
            "body": body,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > MAX_BYTES:
        return {
            "id": "ntfy-writeback",
            "state": "OVERSIZE",
            "verified": False,
            "note": f"{len(payload)} bytes exceeds {MAX_BYTES}",
        }
    last = "no host"
    for host in NTFY_HOSTS:
        url = f"{host}/{WRITE_TOPIC}"
        if CURSOR_TOPIC in url or FRESH_TOPIC in url:
            last = "refused non-write topic"
            continue
        result = http_call(url, data=payload, post=post)
        if result["status"] == 200:
            return {
                "id": "ntfy-writeback",
                "state": "MAILED",
                "verified": True,
                "independent_origin": True,
                "url": url,
                "post_id": post_id,
                "note": "ntfy 200 is mail. The post is p/{id}.md on git HEAD.",
            }
        last = f"http {result['status']}"
    return {"id": "ntfy-writeback", "state": "MISS", "verified": False, "note": last}


def writeback_from_restore(
    restored: Mapping[str, Mapping[str, str]],
    live: Mapping[str, Mapping[str, str]],
    post: Callable[..., int] | None = None,
) -> dict[str, Any]:
    mailed = []
    skipped = []
    conflicts = []
    oversize = []
    for post_id, row in sorted(restored.items()):
        other = live.get(post_id)
        if other and other.get("sha256") == row.get("sha256"):
            skipped.append(post_id)
            continue
        if other and other.get("sha256") != row.get("sha256"):
            conflicts.append(post_id)
            continue
        result = bounded_writeback(
            {"id": post_id, "from": row.get("from") or "UNSEATED", "to": "TABLE", "body": row.get("body") or ""},
            post=post,
        )
        if result["state"] == "MAILED":
            mailed.append(post_id)
        elif result["state"] == "OVERSIZE":
            oversize.append(post_id)
        else:
            skipped.append(post_id)
    state = "CONFLICT" if conflicts else "WRITEBACK"
    return {
        "state": state,
        "mailed": mailed,
        "skipped_identical": skipped,
        "conflicts": conflicts,
        "oversize": oversize,
        "note": "CONFLICT only on same-id disagreement; identical ids are deduped; disjoint ids merge",
    }


def restore_drill(source: Path, workdir: Path) -> dict[str, Any]:
    source = Path(source).resolve()
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(source)
    manifest = repo_backup.snapshot(source, workdir / "backup")
    verified = repo_backup.verify(manifest)
    restored = repo_backup.restore(manifest, workdir / "restored")
    if restored["restored_head_sha"] != snapshot["head_sha"] and restored["restored_head_sha"] != verified["head_sha"]:
        raise MirrorError("restore HEAD disagrees with backup manifest")
    if restored["restored_head_sha"] != verified["head_sha"]:
        raise MirrorError("restore HEAD disagrees with verified bundle")
    blobs = {}
    for row in snapshot["entries"]:
        blobs[row["path"]] = _show_bytes(source, snapshot["head_sha"], row["path"])
    corrupt = detect_corrupt(snapshot, blobs)
    if corrupt:
        raise MirrorError("snapshot corrupt: " + ",".join(corrupt))
    memory_receipt = {
        "id": "memory",
        "verified": True,
        "independent_origin": False,
        "digest": snapshot["digest"],
        "head_sha": snapshot["head_sha"],
    }
    backup_receipt = {
        "id": "repo-backup",
        "verified": True,
        "independent_origin": False,
        "digest": verified["bundle_sha256"],
        "head_sha": verified["head_sha"],
        "manifest": str(manifest),
    }
    preferred = prefer_receipts([backup_receipt, memory_receipt])
    return {
        "state": "RESTORED",
        "head_sha": restored["restored_head_sha"],
        "bundle_sha256": verified["bundle_sha256"],
        "snapshot_digest": snapshot["digest"],
        "preferred": preferred,
        "backup": restored,
        "entries": len(snapshot["entries"]),
    }


def sync(source: Path, live: bool = False, output: Path | None = None) -> dict[str, Any]:
    source = Path(source).resolve()
    snapshot = build_snapshot(source)
    previous = None
    rel = "ancestor"
    state_path = (output or Path(tempfile.gettempdir()) / "moving-main-out") / "cursor-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.is_file():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8"))
            rel = relation(source, str(previous.get("head_sha") or ""), snapshot["head_sha"])
        except (OSError, json.JSONDecodeError, MirrorError):
            previous = None
            rel = "ancestor"
    cursor = advance_cursor(previous, snapshot, rel)
    receipts: list[dict[str, Any]] = []
    if cursor["state"] in {"STALE", "CORRUPT", "CONFLICT"}:
        payload = {
            "state": cursor["state"],
            "cursor": cursor,
            "snapshot": snapshot,
            "receipts": receipts,
            "log": [redact(cursor)],
        }
        state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload
    body = compact_cursor(snapshot, cursor)
    if live and cursor["state"] != "IDEMPOTENT":
        receipts.append(publish_ntfy_cursor(body))
        receipts.append(publish_software_heritage())
        receipts.append(publish_internet_archive())
        receipts.append(publish_jsdelivr_readback())
        ntfy_read = readback_ntfy_cursor(str(cursor["digest"]))
        receipts.append(ntfy_read)
        swh_url = next((row.get("request_url") for row in receipts if row.get("id") == "software-heritage"), None)
        receipts.append(readback_software_heritage(swh_url))
    elif not live:
        receipts.append(
            {
                "id": "ntfy-cursor",
                "state": "DRY",
                "verified": False,
                "independent_origin": True,
                "digest": sha256_hex(body),
            }
        )
    preferred = prefer_receipts(receipts)
    payload = {
        "state": cursor["state"],
        "cursor": cursor,
        "snapshot": {"head_sha": snapshot["head_sha"], "digest": snapshot["digest"], "created_at": snapshot["created_at"], "entries": snapshot["entries"]},
        "receipts": receipts,
        "preferred": preferred,
        "adapters": adapters_catalog()["adapters"],
        "log": [redact(f"{row.get('id')} {row.get('state')} {row.get('status', '')}") for row in receipts],
    }
    keep = {
        "seq": cursor["seq"],
        "head_sha": cursor["head_sha"],
        "digest": cursor["digest"],
        "entries": snapshot["entries"],
        "schema_version": SCHEMA_VERSION,
    }
    if cursor["state"] not in {"STALE", "CORRUPT"}:
        state_path.write_text(json.dumps(keep, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_json = state_path.parent / "last.json"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"state": payload["state"], "head_sha": cursor["head_sha"], "receipts": len(receipts)}, sort_keys=True))
    return payload


def status_payload() -> dict[str, Any]:
    catalog = adapters_catalog()
    return {
        "schema_version": SCHEMA_VERSION,
        "adapters": catalog["adapters"],
        "still_open": catalog["still_open"],
        "compose": catalog["compose"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snap = commands.add_parser("snapshot")
    snap.add_argument("--source", type=Path, default=Path.cwd())
    adv = commands.add_parser("sync")
    adv.add_argument("--source", type=Path, default=Path.cwd())
    adv.add_argument("--live", action="store_true")
    adv.add_argument("--output", type=Path, default=None)
    drill = commands.add_parser("restore-drill")
    drill.add_argument("--source", type=Path, default=Path.cwd())
    drill.add_argument("--workdir", type=Path, default=None)
    commands.add_parser("status")
    wb = commands.add_parser("writeback")
    wb.add_argument("--id", required=True)
    wb.add_argument("--body", required=True)
    wb.add_argument("--from-claim", dest="from_claim", default="UNSEATED")
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            print(json.dumps(build_snapshot(args.source), sort_keys=True))
            return 0
        if args.command == "sync":
            sync(args.source, live=args.live, output=args.output)
            return 0
        if args.command == "restore-drill":
            workdir = args.workdir or Path(tempfile.mkdtemp(prefix="moving-main-drill-"))
            print(json.dumps(restore_drill(args.source, workdir), sort_keys=True, default=str))
            return 0
        if args.command == "status":
            print(json.dumps(status_payload(), sort_keys=True, indent=2))
            return 0
        result = bounded_writeback(
            {"id": args.id, "from": args.from_claim, "to": "TABLE", "body": args.body}
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("state") in {"MAILED", "OVERSIZE"} else 2
    except MirrorError as error:
        print("MIRROR_ERROR: " + redact(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
