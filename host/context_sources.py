"""Exact-commit Git source capsules for Commons context packets."""

from __future__ import annotations

import copy
import hashlib
import hmac
import re
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from host.context_packet import DIGEST_KEY, PacketError, canonical, digest, markdown, verify_packet
except ModuleNotFoundError:
    from context_packet import DIGEST_KEY, PacketError, canonical, digest, markdown, verify_packet

HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_MODES = {"100644", "100755"}
MAX_PATHS = 32
MAX_PATH_LEN = 512


def _git(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[0][:200]}" if detail else ""
        raise PacketError(f"git {' '.join(args[:2])} failed{suffix}")
    return proc.stdout


def _path(raw: str) -> str:
    if type(raw) is not str:
        raise PacketError("source paths must be strings")
    text = raw.strip()
    if not text or len(text) > MAX_PATH_LEN or "\\" in text or "\x00" in text:
        raise PacketError("invalid source path")
    p = PurePosixPath(text)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise PacketError(f"source path must be repository-relative without traversal: {text!r}")
    if text.startswith(":"):
        raise PacketError("source path may not use Git pathspec magic")
    return p.as_posix()


def _text(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PacketError("source blob is not strict UTF-8 text") from exc
    if "\x00" in text or any(ord(ch) < 32 and ch not in "\t\n\r" for ch in text) or "\x7f" in text:
        raise PacketError("source blob contains binary/control bytes")
    return text


def capture_sources(
    repo_root: str | Path,
    commit: str,
    paths: Sequence[str],
    *,
    max_file_bytes: int = 32_768,
    max_excerpt_chars: int = 12_000,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    if not repo.is_dir():
        raise PacketError(f"repo root is not a directory: {repo}")
    if type(commit) is not str or not HEX40.fullmatch(commit):
        raise PacketError("source commit must be an exact lowercase 40-hex commit")
    if type(max_file_bytes) is not int or not 1 <= max_file_bytes <= 1_048_576:
        raise PacketError("max_file_bytes must be 1..1048576")
    if type(max_excerpt_chars) is not int or not 1 <= max_excerpt_chars <= 100_000:
        raise PacketError("max_excerpt_chars must be 1..100000")
    selected = sorted({_path(path) for path in paths})
    if not selected:
        raise PacketError("at least one source path is required")
    if len(selected) > MAX_PATHS:
        raise PacketError(f"source path count exceeds {MAX_PATHS}")
    if _git(repo, "cat-file", "-t", commit).decode().strip() != "commit":
        raise PacketError("source commit does not name a commit object")

    capsules: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    for path in selected:
        raw = _git(repo, "ls-tree", "-z", commit, "--", f":(literal){path}")
        entries = [item for item in raw.split(b"\0") if item]
        if len(entries) != 1:
            raise PacketError(f"source path is missing or ambiguous at commit: {path}")
        try:
            meta, returned_path = entries[0].split(b"\t", 1)
            mode_b, kind_b, blob_b = meta.split(b" ", 2)
            mode, kind, blob = mode_b.decode(), kind_b.decode(), blob_b.decode()
            actual_path = returned_path.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise PacketError(f"malformed ls-tree record for {path}") from exc
        if actual_path != path:
            raise PacketError(f"Git returned unexpected path for {path}")
        if kind != "blob" or mode not in ALLOWED_MODES or not HEX40.fullmatch(blob):
            raise PacketError(f"source path is not an ordinary regular blob: {path} ({mode} {kind})")
        size_text = _git(repo, "cat-file", "-s", blob).decode().strip()
        try:
            size = int(size_text)
        except ValueError as exc:
            raise PacketError(f"invalid Git object size for {path}") from exc
        base = {"path": path, "mode": mode, "blob_sha": blob, "bytes": size}
        if size > max_file_bytes:
            omitted.append({**base, "reason": "file_too_large", "max_file_bytes": max_file_bytes})
            continue
        content = _git(repo, "cat-file", "blob", blob)
        if len(content) != size:
            raise PacketError(f"Git blob size changed while reading {path}")
        sha256 = hashlib.sha256(content).hexdigest()
        try:
            text = _text(content)
        except PacketError:
            omitted.append({**base, "sha256": sha256, "reason": "non_text"})
            continue
        complete = len(text) <= max_excerpt_chars
        excerpt = text if complete else text[:max_excerpt_chars]
        capsules.append({
            **base,
            "sha256": sha256,
            "text": excerpt,
            "text_complete": complete,
            "omitted_text_chars": 0 if complete else len(text) - len(excerpt),
        })
    return {
        "schema": "commons-context-source-capture/v1",
        "commit": commit,
        "paths_requested": selected,
        "capsules": capsules,
        "omitted": omitted,
    }


def attach_sources(packet: Mapping[str, Any], capture: Mapping[str, Any], *, max_chars: int) -> dict[str, Any]:
    ok, reason = verify_packet(packet)
    if not ok:
        raise PacketError(f"base packet is invalid: {reason}")
    if type(max_chars) is not int or max_chars < 2048:
        raise PacketError("max_chars must be >= 2048")
    if capture.get("schema") != "commons-context-source-capture/v1" or not HEX40.fullmatch(str(capture.get("commit") or "")):
        raise PacketError("invalid source capture")
    out = copy.deepcopy(dict(packet))
    out.pop(DIGEST_KEY, None)
    limits = out.get("limits")
    if type(limits) is not dict:
        raise PacketError("packet limits missing")
    limits["max_chars"] = max_chars
    capsules = list(capture.get("capsules") or [])
    omitted = list(capture.get("omitted") or [])
    source = {
        "schema": capture["schema"],
        "commit": capture["commit"],
        "paths_requested": list(capture.get("paths_requested") or []),
        "capsules": [],
        "omitted": omitted,
        "omitted_by_reason": {},
    }
    out["source_context"] = source

    def fit() -> bool:
        probe = copy.deepcopy(out)
        probe[DIGEST_KEY] = "0" * 64
        return len(canonical(probe)) <= max_chars

    if not fit():
        initial_counts = Counter(str(row.get("reason") or "unknown") for row in source["omitted"] if isinstance(row, Mapping))
        source["omitted"] = []
        source["omitted_by_reason"] = dict(sorted(initial_counts.items()))
        source["omitted_metadata_elided"] = True
    if not fit():
        raise PacketError("max_chars is too small for source-capture summary")
    budget_omitted: list[dict[str, Any]] = []
    for capsule in capsules:
        source["capsules"].append(copy.deepcopy(capsule))
        if not fit():
            source["capsules"].pop()
            budget_omitted.append({
                key: capsule[key]
                for key in ("path", "mode", "blob_sha", "sha256", "bytes")
                if key in capsule
            } | {"reason": "packet_budget"})
    source["omitted"].extend(budget_omitted)
    counts = Counter(str(row.get("reason") or "unknown") for row in source["omitted"] if isinstance(row, Mapping))
    source["omitted_by_reason"] = dict(sorted(counts.items()))
    if not fit():
        # Per-file omission metadata is informative but subordinate to the hard budget.
        source["omitted"] = []
        source["omitted_by_reason"] = dict(sorted(counts.items()))
        source["omitted_metadata_elided"] = True
    if not fit():
        raise PacketError("max_chars is too small for source capsule summary")
    out[DIGEST_KEY] = digest(out)
    if len(canonical(out)) > max_chars:
        raise PacketError("packet exceeded max_chars after source attachment")
    return out


def markdown_with_sources(packet: Mapping[str, Any]) -> str:
    text = markdown(packet)
    source = packet.get("source_context")
    if not isinstance(source, Mapping):
        return text
    lines = [text.rstrip(), "", "## Exact Git source capsules", "", f"- Commit: `{source.get('commit','')}`"]
    for capsule in source.get("capsules") or []:
        if not isinstance(capsule, Mapping):
            continue
        body = str(capsule.get("text") or "")
        longest = max((len(run) for run in re.findall(r"`+", body)), default=0)
        fence = "`" * max(3, longest + 1)
        lines.extend([
            "",
            f"### `{capsule.get('path','')}`",
            "",
            f"Mode `{capsule.get('mode','')}` · blob `{capsule.get('blob_sha','')}` · SHA-256 `{capsule.get('sha256','')}` · bytes `{capsule.get('bytes','')}` · complete `{capsule.get('text_complete')}`",
            "",
            fence + "text",
            body,
            fence,
        ])
    omitted = source.get("omitted_by_reason") or {}
    if omitted:
        lines.extend(["", f"Omitted source capsules: `{canonical(omitted)}`"])
    return "\n".join(lines) + "\n"
