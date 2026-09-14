"""Exact committed-tree Git source capsules for Commons context packets."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
ORDINARY_BLOB_MODES = {"100644", "100755"}
MAX_SOURCE_PATHS = 32
MAX_FILE_BYTES_CEILING = 1_048_576
GIT_SOURCE_KEYS = {
    "commit",
    "tree_sha",
    "observed_main_head",
    "source_commit_matches_observed_main",
    "max_file_bytes",
    "requested_paths",
    "capsules",
}
CAPSULE_BASE_KEYS = {"path", "mode", "blob_sha", "content_sha256", "bytes", "text_included"}
CAPSULE_OMISSION_REASONS = {"FILE_TOO_LARGE", "NON_UTF8", "NON_TEXT_CONTROL", "PACKET_BUDGET"}
GIT_REPOSITORY_REDIRECT_ENV = {
    "GIT_DIR",
    "GIT_COMMON_DIR",
    "GIT_WORK_TREE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_INDEX_FILE",
    "GIT_SHALLOW_FILE",
}
GIT_PATHSPEC_ENV = {
    "GIT_LITERAL_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
}


class GitSourceError(ValueError):
    pass


def _git_env() -> dict[str, str]:
    """Return a local, exact-repository, literal-path Git environment."""
    env = os.environ.copy()
    # ``git -C repo`` does not override inherited repository-routing variables such
    # as GIT_DIR. Remove every repository/object-store redirect so the explicit
    # repository argument is the authority boundary. Pathspec policy is likewise
    # process-owned so an inherited icase/glob mode cannot change path resolution.
    for key in GIT_REPOSITORY_REDIRECT_ENV | GIT_PATHSPEC_ENV:
        env.pop(key, None)
    env["GIT_LITERAL_PATHSPECS"] = "1"
    # Exact-source reads are local-only: replacement objects and promisor-remote
    # lazy fetches may not supply bytes outside the selected local object database.
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    env["GIT_NO_LAZY_FETCH"] = "1"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _run(repo: Path, args: Sequence[str], *, input_bytes: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=_git_env(),
        )
    except OSError as exc:
        raise GitSourceError(f"git unavailable: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise GitSourceError(f"git command failed: {' '.join(args)}: {detail[:240]}")
    return proc.stdout


def _canonical_path(raw: str) -> str:
    if not isinstance(raw, str):
        raise GitSourceError("source path must be a string")
    if not raw or raw != raw.strip() or len(raw) > 512:
        raise GitSourceError("source path must be 1..512 canonical characters")
    if raw.startswith("/") or "\\" in raw or "\x00" in raw or raw.startswith(":"):
        raise GitSourceError(f"unsafe source path: {raw!r}")
    if any(ch in raw for ch in "*?[]"):
        raise GitSourceError(f"pathspec metacharacters are not allowed: {raw!r}")
    pieces = raw.split("/")
    if any(piece in ("", ".", "..") for piece in pieces):
        raise GitSourceError(f"non-canonical source path: {raw!r}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise GitSourceError(f"control character in source path: {raw!r}")
    return raw


def _object_type(repo: Path, oid: str) -> str:
    return _run(repo, ["cat-file", "-t", oid]).decode("ascii", "strict").strip()


def _commit_tree(repo: Path, commit: str) -> str:
    raw = _run(repo, ["cat-file", "-p", commit])
    for line in raw.split(b"\n"):
        if line.startswith(b"tree "):
            try:
                tree = line[5:].decode("ascii", "strict")
            except UnicodeDecodeError as exc:
                raise GitSourceError("commit has malformed tree header") from exc
            if HEX40.fullmatch(tree):
                return tree
            break
    raise GitSourceError("commit has no canonical 40-hex tree")


def _observed_main(repo: Path) -> str | None:
    try:
        raw = _run(repo, ["rev-parse", "--verify", "refs/heads/main"]).decode("ascii", "strict").strip()
    except GitSourceError:
        return None
    return raw if HEX40.fullmatch(raw) else None


def _tree_entry(repo: Path, commit: str, path: str) -> tuple[str, str, str]:
    raw = _run(repo, ["ls-tree", "-z", "--full-tree", commit, "--", path])
    rows = [row for row in raw.split(b"\x00") if row]
    if len(rows) != 1:
        raise GitSourceError(f"source path must resolve to exactly one committed entry: {path}")
    try:
        meta, returned = rows[0].split(b"\t", 1)
        mode_b, typ_b, oid_b = meta.split(b" ", 2)
        mode = mode_b.decode("ascii", "strict")
        typ = typ_b.decode("ascii", "strict")
        oid = oid_b.decode("ascii", "strict")
        returned_path = returned.decode("utf-8", "strict")
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitSourceError(f"malformed ls-tree result for {path}") from exc
    if returned_path != path:
        raise GitSourceError(f"source path resolved ambiguously: requested {path!r}, got {returned_path!r}")
    if typ != "blob" or mode not in ORDINARY_BLOB_MODES or not HEX40.fullmatch(oid):
        raise GitSourceError(f"source path is not an ordinary committed blob: {path} mode={mode} type={typ}")
    return mode, typ, oid


def _blob(repo: Path, oid: str, expected_size: int, collect_limit: int) -> tuple[str, bytes | None]:
    try:
        proc = subprocess.Popen(
            ["git", "-C", str(repo), "cat-file", "blob", oid],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_env(),
        )
    except OSError as exc:
        raise GitSourceError(f"git unavailable: {exc}") from exc
    if proc.stdout is None:
        proc.kill()
        raise GitSourceError("git cat-file stdout unavailable")
    hasher = hashlib.sha256()
    collected = bytearray() if expected_size <= collect_limit else None
    seen = 0
    while True:
        chunk = proc.stdout.read(65536)
        if not chunk:
            break
        seen += len(chunk)
        hasher.update(chunk)
        if collected is not None:
            collected.extend(chunk)
    if proc.stdout is not None:
        proc.stdout.close()
    stderr = proc.stderr.read() if proc.stderr is not None else b""
    if proc.stderr is not None:
        proc.stderr.close()
    code = proc.wait()
    if code != 0:
        raise GitSourceError(f"git cat-file blob failed: {stderr.decode('utf-8', 'replace')[:240]}")
    if seen != expected_size:
        raise GitSourceError(f"blob size changed while reading {oid}: expected {expected_size}, got {seen}")
    return hasher.hexdigest(), bytes(collected) if collected is not None else None


def _text_status(raw: bytes | None, *, oversized: bool) -> tuple[str | None, str | None]:
    if oversized:
        return None, "FILE_TOO_LARGE"
    if raw is None:
        raise GitSourceError("blob bytes unavailable below collection limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None, "NON_UTF8"
    if any((ord(ch) < 32 and ch not in "\n\r\t") or ord(ch) == 127 for ch in text):
        return None, "NON_TEXT_CONTROL"
    return text, None


def collect_git_source(
    repository: str | Path,
    commit: str,
    paths: Sequence[str],
    *,
    max_file_bytes: int = 16_384,
) -> dict[str, Any]:
    """Read only exact committed Git objects for explicitly requested paths."""
    repo = Path(repository)
    if not repo.is_dir():
        raise GitSourceError(f"repository path is not a directory: {repo}")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise GitSourceError("source commit must be exact lowercase 40-hex")
    if type(max_file_bytes) is not int or not (1 <= max_file_bytes <= MAX_FILE_BYTES_CEILING):
        raise GitSourceError(f"max_file_bytes must be 1..{MAX_FILE_BYTES_CEILING}")
    if isinstance(paths, (str, bytes)):
        raise GitSourceError("source paths must be a sequence of explicit paths")
    canonical_paths = sorted({_canonical_path(path) for path in paths})
    if not canonical_paths:
        raise GitSourceError("at least one explicit source path is required")
    if len(canonical_paths) > MAX_SOURCE_PATHS:
        raise GitSourceError(f"source path count exceeds {MAX_SOURCE_PATHS}")
    if _object_type(repo, commit) != "commit":
        raise GitSourceError("source commit does not name a commit object")

    tree_sha = _commit_tree(repo, commit)
    observed_main = _observed_main(repo)
    capsules: list[dict[str, Any]] = []
    for path in canonical_paths:
        mode, _, blob_sha = _tree_entry(repo, commit, path)
        size_text = _run(repo, ["cat-file", "-s", blob_sha]).decode("ascii", "strict").strip()
        try:
            size = int(size_text)
        except ValueError as exc:
            raise GitSourceError(f"invalid blob size for {path}") from exc
        if size < 0:
            raise GitSourceError(f"negative blob size for {path}")
        content_sha256, raw = _blob(repo, blob_sha, size, max_file_bytes)
        text, reason = _text_status(raw, oversized=size > max_file_bytes)
        row: dict[str, Any] = {
            "path": path,
            "mode": mode,
            "blob_sha": blob_sha,
            "content_sha256": content_sha256,
            "bytes": size,
        }
        if text is None:
            row["text"] = None
            row["source_omission_reason"] = reason
        else:
            row["text"] = text
        capsules.append(row)

    return {
        "commit": commit,
        "tree_sha": tree_sha,
        "observed_main_head": observed_main,
        "source_commit_matches_observed_main": None if observed_main is None else observed_main == commit,
        "max_file_bytes": max_file_bytes,
        "requested_paths": canonical_paths,
        "capsules": capsules,
    }


def _validate_packet_capsule(row: Any) -> tuple[bool, str]:
    """Validate exact packet capsule schema before equality/coercion is possible."""
    if type(row) is not dict:
        return False, "git-source-capsule-shape"
    included = row.get("text_included")
    if type(included) is not bool:
        return False, "git-source-inclusion-flag"
    expected_keys = CAPSULE_BASE_KEYS | ({"text"} if included else {"omission_reason"})
    if set(row) != expected_keys:
        return False, "git-source-capsule-shape"
    path = row.get("path")
    try:
        if type(path) is not str or _canonical_path(path) != path:
            return False, "git-source-path"
    except GitSourceError:
        return False, "git-source-path"
    if type(row.get("mode")) is not str or row["mode"] not in ORDINARY_BLOB_MODES:
        return False, "git-source-mode"
    if type(row.get("blob_sha")) is not str or not HEX40.fullmatch(row["blob_sha"]):
        return False, "git-source-blob-sha"
    if type(row.get("content_sha256")) is not str or not HEX64.fullmatch(row["content_sha256"]):
        return False, "git-source-content-sha256"
    if type(row.get("bytes")) is not int or row["bytes"] < 0:
        return False, "git-source-bytes"
    if included:
        if type(row.get("text")) is not str:
            return False, "git-source-text"
    else:
        if type(row.get("omission_reason")) is not str or row["omission_reason"] not in CAPSULE_OMISSION_REASONS:
            return False, "git-source-omission"
    return True, "ok"


def verify_git_source(bundle: Any, repository: str | Path) -> tuple[bool, str]:
    """Re-read committed objects and verify packet source metadata/text against them."""
    if type(bundle) is not dict or set(bundle) != GIT_SOURCE_KEYS:
        return False, "git-source-shape"
    commit = bundle.get("commit")
    tree_sha = bundle.get("tree_sha")
    observed_main = bundle.get("observed_main_head")
    source_matches_main = bundle.get("source_commit_matches_observed_main")
    requested = bundle.get("requested_paths")
    max_file_bytes = bundle.get("max_file_bytes")
    capsules = bundle.get("capsules")
    if type(commit) is not str or not HEX40.fullmatch(commit):
        return False, "git-source-commit"
    if type(tree_sha) is not str or not HEX40.fullmatch(tree_sha):
        return False, "git-source-tree-sha"
    if observed_main is not None and (type(observed_main) is not str or not HEX40.fullmatch(observed_main)):
        return False, "git-source-observed-main-head"
    if source_matches_main is not None and type(source_matches_main) is not bool:
        return False, "git-source-main-match"
    if type(max_file_bytes) is not int or not (1 <= max_file_bytes <= MAX_FILE_BYTES_CEILING):
        return False, "git-source-max-file-bytes"
    if type(requested) is not list or not all(type(path) is str for path in requested) or type(capsules) is not list:
        return False, "git-source-shape"
    for packet_row in capsules:
        valid, reason = _validate_packet_capsule(packet_row)
        if not valid:
            return False, reason
    try:
        expected = collect_git_source(repository, commit, requested, max_file_bytes=max_file_bytes)
    except (GitSourceError, TypeError):
        return False, "git-source-read"
    for key in ("commit", "tree_sha", "max_file_bytes", "requested_paths"):
        if bundle.get(key) != expected.get(key):
            return False, f"git-source-{key.replace('_', '-')}"
    # observed main is drift metadata, never source authority; it may legitimately move later.
    actual_by_path = {row["path"]: row for row in expected["capsules"]}
    if len(actual_by_path) != len(capsules):
        return False, "git-source-capsule-count"
    for packet_row in capsules:
        path = packet_row["path"]
        actual = actual_by_path.get(path)
        if actual is None:
            return False, "git-source-path"
        for key in ("mode", "blob_sha", "content_sha256", "bytes"):
            if packet_row[key] != actual.get(key):
                return False, f"git-source-{key.replace('_', '-')}"
        if packet_row["text_included"] is True:
            if packet_row["text"] != actual.get("text") or actual.get("text") is None:
                return False, "git-source-text"
        else:
            reason = packet_row["omission_reason"]
            if actual.get("text") is None:
                if reason != actual.get("source_omission_reason"):
                    return False, "git-source-omission"
            elif reason != "PACKET_BUDGET":
                return False, "git-source-omission"
    return True, "ok"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def verify_packet_git_source(packet: Any, repository: str | Path) -> tuple[bool, str]:
    """Re-read Git and replay compile-time source admission for a semantic-valid packet."""
    if not isinstance(packet, dict):
        return False, "git-source-packet-shape"
    source = packet.get("git_source")
    if source is None:
        return True, "ok"
    if not isinstance(source, dict):
        return False, "git-source-shape"
    ok, _ = verify_git_source(source, repository)
    if not ok:
        return False, "git-source-readback"
    try:
        actual = collect_git_source(
            repository,
            source["commit"],
            source["requested_paths"],
            max_file_bytes=source["max_file_bytes"],
        )
        limits = packet["limits"]
        max_chars = limits["max_chars"]
        omitted_final = packet["omitted"]
        recent_final = packet["recent"]
        resources_final = packet["resources"]
    except (GitSourceError, KeyError, TypeError):
        return False, "git-source-packet-shape"
    if type(max_chars) is not int or max_chars < 0:
        return False, "git-source-packet-shape"
    if not isinstance(omitted_final, dict) or not isinstance(recent_final, list) or not isinstance(resources_final, list):
        return False, "git-source-packet-shape"
    for key in ("claims", "coordination", "recent", "resources", "git_source_text_files", "git_source_text_bytes"):
        if type(omitted_final.get(key)) is not int or omitted_final[key] < 0:
            return False, "git-source-omitted-shape"

    packet_rows = source.get("capsules")
    if not isinstance(packet_rows, list):
        return False, "git-source-shape"
    omitted_rows = [row for row in packet_rows if row["text_included"] is False]
    omitted_files = len(omitted_rows)
    omitted_bytes = sum(row["bytes"] for row in omitted_rows)
    if omitted_final.get("git_source_text_files") != omitted_files:
        return False, "git-source-omitted-files"
    if omitted_final.get("git_source_text_bytes") != omitted_bytes:
        return False, "git-source-omitted-bytes"

    actual_by_path = {row["path"]: row for row in actual["capsules"]}
    # Restore the exact packet boundary used by compile_packet immediately before source
    # text admission: claims/coordination are final, recent/resources are not admitted yet,
    # and every source row is metadata-only. Final included+omitted recovers the later
    # section pool counts without requiring the original input files.
    probe = copy.deepcopy(packet)
    probe.pop("semantic_sha256", None)
    probe["recent"] = []
    probe["resources"] = []
    omitted = dict(probe["omitted"])
    omitted["recent"] = omitted_final["recent"] + len(recent_final)
    omitted["resources"] = omitted_final["resources"] + len(resources_final)
    probe["omitted"] = omitted
    source_probe = probe.get("git_source")
    if not isinstance(source_probe, dict) or not isinstance(source_probe.get("capsules"), list):
        return False, "git-source-shape"
    for row in source_probe["capsules"]:
        if not isinstance(row, dict):
            return False, "git-source-capsule-shape"
        actual_row = actual_by_path.get(row.get("path"))
        if actual_row is None:
            return False, "git-source-path"
        row.pop("text", None)
        row["text_included"] = False
        if actual_row.get("text") is None:
            row["omission_reason"] = actual_row.get("source_omission_reason")
        else:
            row["omission_reason"] = "PACKET_BUDGET"
    omitted["git_source_text_files"] = len(source_probe["capsules"])
    omitted["git_source_text_bytes"] = sum(row["bytes"] for row in source_probe["capsules"])

    def size() -> int:
        sized = copy.deepcopy(probe)
        sized["semantic_sha256"] = "0" * 64
        return len(_canonical(sized))

    by_path = {row["path"]: row for row in source_probe["capsules"]}
    requested = source.get("requested_paths")
    if not isinstance(requested, list):
        return False, "git-source-shape"
    for path in requested:
        actual_row = actual_by_path.get(path)
        row = by_path.get(path)
        if actual_row is None or row is None:
            return False, "git-source-path"
        text = actual_row.get("text")
        if text is None:
            continue
        row["text"] = text
        row["text_included"] = True
        row.pop("omission_reason", None)
        omitted["git_source_text_files"] -= 1
        omitted["git_source_text_bytes"] -= row["bytes"]
        if size() > max_chars:
            row.pop("text", None)
            row["text_included"] = False
            row["omission_reason"] = "PACKET_BUDGET"
            omitted["git_source_text_files"] += 1
            omitted["git_source_text_bytes"] += row["bytes"]

    expected_by_path = {row["path"]: row for row in source_probe["capsules"]}
    for packet_row in packet_rows:
        if not isinstance(packet_row, dict):
            return False, "git-source-capsule-shape"
        expected = expected_by_path.get(packet_row.get("path"))
        if expected is None:
            return False, "git-source-path"
        for key in ("text_included", "omission_reason", "text"):
            if packet_row.get(key) != expected.get(key) or (key in packet_row) != (key in expected):
                return False, "git-source-admission"
    return True, "ok"
