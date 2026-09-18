from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shlex
import stat
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

JOB_SCHEMA = "e2b_exact_head_job.v1"
RECEIPT_SCHEMA = "e2b_exact_head_receipt.v1"
PROVENANCE = "OFF_OWNER_MACHINE_PROVIDER_EXECUTION"
COMMIT_BINDING = "CALLER_ASSERTED_UNVERIFIED"
_PROVIDER = "e2b"

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ALLOWED_JOB_KEYS = {
    "schema",
    "repository",
    "commit_sha",
    "source_archive_sha256",
    "archive_path",
    "template",
    "sandbox_timeout_seconds",
    "commands",
    "manifest",
}
_ALLOWED_COMMAND_KEYS = {"argv", "timeout_seconds"}
_ALLOWED_MANIFEST_KEYS = {"path", "sha256"}
_MAX_COMMANDS = 64
_MAX_ARGV = 64
_MAX_ARG_CHARS = 8192
_MAX_EXCERPT_CHARS = 4096
_MAX_TIMEOUT_SECONDS = 3600
MAX_JOB_PACKET_BYTES = 1 * 1024 * 1024
MAX_SOURCE_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_ENTRIES = 8192
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_MEMBER_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_JOB_JSON_DEPTH = 32
MAX_JOB_JSON_NODES = 100_000

_ARCHIVE_REMOTE = "/tmp/e2b-exact-head-source.archive"
_MANIFEST_REMOTE = "/tmp/e2b-exact-head-manifest.json"
_WORKSPACE_REMOTE = "/workspace/source"


class JobValidationError(ValueError):
    """Raised before any provider construction for an invalid or untrusted job."""


class ProviderExecutionError(RuntimeError):
    """Raised after provider construction when custody/preflight execution fails."""


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    timeout_seconds: int


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    sha256: str


@dataclass(frozen=True)
class JobSpec:
    repository: str
    commit_sha: str
    source_archive_sha256: str
    archive_path: str
    template: str
    sandbox_timeout_seconds: int
    commands: tuple[CommandSpec, ...]
    manifest: tuple[ManifestEntry, ...]
    job_sha256: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JobValidationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise JobValidationError(f"non-finite JSON number rejected: {value}")


def _strict_float(value: str) -> float:
    try:
        parsed = float(value)
    except (OverflowError, ValueError) as exc:
        raise JobValidationError("invalid JSON float") from exc
    if not (float("-inf") < parsed < float("inf")):
        raise JobValidationError("non-finite JSON number rejected")
    return parsed


def _check_json_shape(value: Any) -> None:
    remaining = MAX_JOB_JSON_NODES
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        remaining -= 1
        if remaining < 0 or depth > MAX_JOB_JSON_DEPTH:
            raise JobValidationError("job JSON structure exceeds limits")
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)


def parse_job_packet_text(text: str) -> Mapping[str, Any]:
    if not isinstance(text, str):
        raise JobValidationError("job JSON must be text")
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise JobValidationError("job JSON must be valid UTF-8") from exc
    if len(encoded) > MAX_JOB_PACKET_BYTES:
        raise JobValidationError("job JSON exceeds byte limit")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
            parse_float=_strict_float,
        )
    except JobValidationError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError, TypeError) as exc:
        raise JobValidationError(f"invalid job JSON: {exc}") from exc
    _check_json_shape(value)
    if not isinstance(value, Mapping):
        raise JobValidationError("job packet must be an object")
    return value


def _read_archive_bounded(path: Path) -> tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise JobValidationError("archive_path must name a readable regular non-symlink file") from exc
    digest = hashlib.sha256()
    payload = bytearray()
    try:
        with os.fdopen(fd, "rb", closefd=True) as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise JobValidationError("archive_path must name a regular file")
            while True:
                chunk = handle.read(min(1024 * 1024, MAX_SOURCE_ARCHIVE_BYTES + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > MAX_SOURCE_ARCHIVE_BYTES:
                    raise JobValidationError("source archive exceeds byte limit")
                digest.update(chunk)
    except Exception:
        raise
    return bytes(payload), digest.hexdigest()


def _safe_archive_path(raw: str) -> bool:
    if not raw or len(raw) > 4096:
        return False
    posix = PurePosixPath(raw)
    return not posix.is_absolute() and all(part not in {"", ".", ".."} for part in posix.parts)


def _account_archive_member(size: int, count: int, total: int) -> tuple[int, int]:
    count += 1
    if count > MAX_ARCHIVE_MEMBERS:
        raise JobValidationError("archive member count exceeds limit")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise JobValidationError("archive member size is invalid")
    if size > MAX_ARCHIVE_MEMBER_BYTES:
        raise JobValidationError("archive member exceeds uncompressed byte limit")
    total += size
    if total > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise JobValidationError("archive total uncompressed bytes exceed limit")
    return count, total


def _preflight_archive_bytes(payload: bytes) -> None:
    count = 0
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
            for member in archive:
                if (
                    not _safe_archive_path(member.name)
                    or member.issym()
                    or member.islnk()
                    or not (member.isfile() or member.isdir())
                ):
                    raise JobValidationError("archive contains unsafe tar member")
                count, total = _account_archive_member(
                    member.size if member.isfile() else 0, count, total
                )
        return
    except JobValidationError:
        raise
    except (tarfile.TarError, OSError, EOFError):
        pass

    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for info in archive.infolist():
                mode = (info.external_attr >> 16) & 0o170000
                if (
                    not _safe_archive_path(info.filename)
                    or mode not in (0, 0o040000, 0o100000)
                ):
                    raise JobValidationError("archive contains unsafe zip member")
                count, total = _account_archive_member(
                    0 if info.is_dir() else info.file_size, count, total
                )
        return
    except JobValidationError:
        raise
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise JobValidationError("source archive must be a valid tar or zip archive") from exc


def _require_exact_keys(value: Mapping[str, Any], allowed: set[str], where: str) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise JobValidationError(f"{where} contains unsupported keys: {', '.join(extras)}")


def _positive_int(value: Any, where: str, *, maximum: int = _MAX_TIMEOUT_SECONDS) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > maximum:
        raise JobValidationError(f"{where} must be an integer in [1, {maximum}]")
    return value


def _safe_manifest_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > 4096:
        raise JobValidationError("manifest path must be a non-empty bounded string")
    posix = PurePosixPath(raw)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise JobValidationError(f"manifest path is not a safe relative path: {raw!r}")
    return posix.as_posix()


def validate_job(packet: Mapping[str, Any]) -> JobSpec:
    if not isinstance(packet, Mapping):
        raise JobValidationError("job packet must be an object")
    _require_exact_keys(packet, _ALLOWED_JOB_KEYS, "job packet")
    if packet.get("schema") != JOB_SCHEMA:
        raise JobValidationError(f"schema must be exactly {JOB_SCHEMA!r}")

    repository = packet.get("repository")
    if not isinstance(repository, str) or not _REPOSITORY_RE.fullmatch(repository):
        raise JobValidationError("repository must be owner/name")

    commit_sha = packet.get("commit_sha")
    if not isinstance(commit_sha, str) or not _SHA40_RE.fullmatch(commit_sha):
        raise JobValidationError("commit_sha must be exactly 40 lowercase hexadecimal characters")

    source_digest = packet.get("source_archive_sha256")
    if not isinstance(source_digest, str) or not _SHA256_RE.fullmatch(source_digest):
        raise JobValidationError("source_archive_sha256 must be exactly 64 lowercase hexadecimal characters")

    archive_path = packet.get("archive_path")
    if not isinstance(archive_path, str) or not archive_path or "\x00" in archive_path:
        raise JobValidationError("archive_path must be a non-empty local path string")

    template = packet.get("template")
    if not isinstance(template, str) or not template.strip() or len(template) > 256:
        raise JobValidationError("template must be a non-empty string no longer than 256 characters")

    sandbox_timeout = _positive_int(packet.get("sandbox_timeout_seconds"), "sandbox_timeout_seconds")

    raw_commands = packet.get("commands")
    if not isinstance(raw_commands, list) or not raw_commands or len(raw_commands) > _MAX_COMMANDS:
        raise JobValidationError(f"commands must contain 1..{_MAX_COMMANDS} command objects")
    commands: list[CommandSpec] = []
    timeout_sum = 0
    for index, raw in enumerate(raw_commands):
        if not isinstance(raw, Mapping):
            raise JobValidationError(f"commands[{index}] must be an object")
        _require_exact_keys(raw, _ALLOWED_COMMAND_KEYS, f"commands[{index}]")
        argv = raw.get("argv")
        if not isinstance(argv, list) or not argv or len(argv) > _MAX_ARGV:
            raise JobValidationError(f"commands[{index}].argv must contain 1..{_MAX_ARGV} strings")
        checked: list[str] = []
        for arg_index, arg in enumerate(argv):
            if not isinstance(arg, str) or "\x00" in arg or len(arg) > _MAX_ARG_CHARS:
                raise JobValidationError(
                    f"commands[{index}].argv[{arg_index}] must be a bounded NUL-free string"
                )
            checked.append(arg)
        timeout = _positive_int(raw.get("timeout_seconds"), f"commands[{index}].timeout_seconds")
        timeout_sum += timeout
        commands.append(CommandSpec(tuple(checked), timeout))
    if timeout_sum > sandbox_timeout:
        raise JobValidationError("sum(command timeouts) must not exceed sandbox_timeout_seconds")

    raw_manifest = packet.get("manifest", [])
    if not isinstance(raw_manifest, list):
        raise JobValidationError("manifest must be a list when supplied")
    if len(raw_manifest) > MAX_MANIFEST_ENTRIES:
        raise JobValidationError(f"manifest must contain at most {MAX_MANIFEST_ENTRIES} entries")
    manifest: list[ManifestEntry] = []
    seen_paths: set[str] = set()
    for index, raw in enumerate(raw_manifest):
        if not isinstance(raw, Mapping):
            raise JobValidationError(f"manifest[{index}] must be an object")
        _require_exact_keys(raw, _ALLOWED_MANIFEST_KEYS, f"manifest[{index}]")
        path = _safe_manifest_path(raw.get("path"))
        digest = raw.get("sha256")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise JobValidationError(
                f"manifest[{index}].sha256 must be 64 lowercase hexadecimal characters"
            )
        if path in seen_paths:
            raise JobValidationError(f"duplicate manifest path: {path}")
        seen_paths.add(path)
        manifest.append(ManifestEntry(path, digest))

    semantic_packet = {
        "schema": JOB_SCHEMA,
        "repository": repository,
        "commit_sha": commit_sha,
        "source_archive_sha256": source_digest,
        "template": template,
        "sandbox_timeout_seconds": sandbox_timeout,
        "commands": [
            {"argv": list(command.argv), "timeout_seconds": command.timeout_seconds}
            for command in commands
        ],
        "manifest": [{"path": entry.path, "sha256": entry.sha256} for entry in manifest],
    }
    return JobSpec(
        repository=repository,
        commit_sha=commit_sha,
        source_archive_sha256=source_digest,
        archive_path=archive_path,
        template=template,
        sandbox_timeout_seconds=sandbox_timeout,
        commands=tuple(commands),
        manifest=tuple(manifest),
        job_sha256=_sha256_bytes(_canonical_bytes(semantic_packet)),
    )


def _result_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def _redact(text: str, secrets: Sequence[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED_E2B_API_KEY]")
    return redacted


def _excerpt(text: str, secrets: Sequence[str]) -> str:
    return _redact(text, secrets)[:_MAX_EXCERPT_CHARS]


def _command_result(
    result: Any,
    order: int,
    command: CommandSpec,
    secrets: Sequence[str],
) -> dict[str, Any]:
    stdout = _result_text(getattr(result, "stdout", ""))
    stderr = _result_text(getattr(result, "stderr", ""))
    exit_code = getattr(result, "exit_code", None)
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        raise ProviderExecutionError("provider command result omitted integer exit_code")
    return {
        "order": order,
        "argv": [_redact(arg, secrets) for arg in command.argv],
        "timeout_seconds": command.timeout_seconds,
        "exit_code": exit_code,
        "stdout_sha256": _sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": _sha256_bytes(stderr.encode("utf-8")),
        "stdout_excerpt": _excerpt(stdout, secrets),
        "stderr_excerpt": _excerpt(stderr, secrets),
    }


def _provider_run(sandbox: Any, command: str, timeout: int, *, cwd: str | None = None) -> Any:
    kwargs: dict[str, Any] = {"timeout": timeout}
    if cwd is not None:
        kwargs["cwd"] = cwd
    return sandbox.commands.run(command, **kwargs)


def _checked_internal_stage(
    sandbox: Any,
    stage: str,
    script: str,
    timeout: int,
    *,
    args: Sequence[str] = (),
) -> str:
    marker = f"# E2B_STAGE_{stage}\n"
    argv = ["python", "-c", marker + script, *args]
    result = _provider_run(sandbox, shlex.join(argv), timeout)
    exit_code = getattr(result, "exit_code", None)
    if exit_code != 0:
        stderr = _result_text(getattr(result, "stderr", ""))
        raise ProviderExecutionError(
            f"{stage} failed with exit_code={exit_code}: {stderr[:512]}"
        )
    return _result_text(getattr(result, "stdout", "")).strip()


_ARCHIVE_DIGEST_SCRIPT = r"""
import hashlib
import pathlib
import sys
p = pathlib.Path(sys.argv[1])
h = hashlib.sha256()
with p.open("rb") as f:
    while True:
        b = f.read(1048576)
        if not b:
            break
        h.update(b)
print(h.hexdigest())
"""

_SAFE_EXTRACT_SCRIPT = r"""
import pathlib
import sys
import tarfile
import zipfile

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
max_members = int(sys.argv[3])
max_member_bytes = int(sys.argv[4])
max_total_bytes = int(sys.argv[5])
dst.mkdir(parents=True, exist_ok=True)

def safe(name):
    p = pathlib.PurePosixPath(name)
    return (not p.is_absolute()) and bool(p.parts) and all(
        part not in ("", ".", "..") for part in p.parts
    )

def account(size, count, total):
    count += 1
    if count > max_members:
        raise SystemExit(95)
    if size < 0 or size > max_member_bytes:
        raise SystemExit(96)
    total += size
    if total > max_total_bytes:
        raise SystemExit(97)
    return count, total

if tarfile.is_tarfile(src):
    count = total = 0
    with tarfile.open(src, "r:*") as tf:
        for member in tf:
            if (
                not safe(member.name)
                or member.issym()
                or member.islnk()
                or not (member.isfile() or member.isdir())
            ):
                raise SystemExit(91)
            count, total = account(member.size if member.isfile() else 0, count, total)
    with tarfile.open(src, "r:*") as tf:
        tf.extractall(dst)
elif zipfile.is_zipfile(src):
    count = total = 0
    with zipfile.ZipFile(src) as zf:
        infos = zf.infolist()
        for info in infos:
            if not safe(info.filename):
                raise SystemExit(92)
            mode = (info.external_attr >> 16) & 0o170000
            if mode not in (0, 0o040000, 0o100000):
                raise SystemExit(93)
            count, total = account(0 if info.is_dir() else info.file_size, count, total)
        zf.extractall(dst)
else:
    raise SystemExit(94)
"""

_MANIFEST_SCRIPT = r"""
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
manifest = json.loads(pathlib.Path(sys.argv[2]).read_text("utf-8"))
for item in manifest:
    target = (root / item["path"]).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise SystemExit(81)
    if not target.is_file() or target.is_symlink():
        raise SystemExit(82)
    h = hashlib.sha256()
    with target.open("rb") as f:
        while True:
            b = f.read(1048576)
            if not b:
                break
            h.update(b)
    if h.hexdigest() != item["sha256"]:
        raise SystemExit(83)
print("manifest-ok")
"""


def _default_sandbox_factory(template: str, timeout_seconds: int, api_key: str) -> Any:
    try:
        from e2b import Sandbox  # type: ignore
    except Exception as exc:
        raise ProviderExecutionError(
            f"E2B SDK unavailable: {type(exc).__name__}: {exc}"
        ) from exc
    try:
        return Sandbox.create(
            template=template,
            timeout=timeout_seconds,
            api_key=api_key,
        )
    except Exception as exc:
        raise ProviderExecutionError(
            f"E2B sandbox creation failed: {type(exc).__name__}: {exc}"
        ) from exc


def _sandbox_id(sandbox: Any) -> str | None:
    value = getattr(sandbox, "sandbox_id", None)
    if value is None:
        value = getattr(sandbox, "id", None)
    return None if value is None else str(value)


def _finalize_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    digest = _sha256_bytes(_canonical_bytes(payload))
    return {**payload, "receipt_sha256": digest}


def execute_job(
    packet: Mapping[str, Any],
    *,
    sandbox_factory: Callable[[str, int, str], Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Execute one caller-supplied source archive inside one E2B sandbox.

    The archive SHA-256 is independently reverified locally and inside E2B.
    Repository and commit_sha remain caller assertions; this adapter does not
    authenticate Git origin and its receipt keeps git_commit_binding_verified false.
    A separate GitHub/source-custody receipt may be composed with this execution
    receipt when exact-head provenance is required.

    Job/schema validation and the local archive digest happen before any provider
    construction. Provider/runtime failures return structured non-green receipts.
    Invalid/untrusted inputs raise JobValidationError and do not contact E2B.
    """
    job = validate_job(packet)
    archive = Path(job.archive_path)
    if archive.is_symlink():
        raise JobValidationError("archive_path must not be a symlink")
    archive_bytes, local_digest = _read_archive_bounded(archive)
    if local_digest != job.source_archive_sha256:
        raise JobValidationError(
            "local source archive digest does not match source_archive_sha256"
        )
    _preflight_archive_bytes(archive_bytes)

    env = os.environ if environ is None else environ
    api_key = env.get("E2B_API_KEY", "")
    secret_values = [api_key] if api_key else []
    base: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "provider": _PROVIDER,
        "provenance": PROVENANCE,
        "repository": job.repository,
        "commit_sha": job.commit_sha,
        "source_archive_sha256": job.source_archive_sha256,
        "job_sha256": job.job_sha256,
        "commit_binding": COMMIT_BINDING,
        "sandbox_id": None,
        "commands": [],
        "kill_attempted": False,
        "kill_succeeded": None,
        "green": False,
        "error": None,
        "truth_boundary": {
            "github_hosted_ci": False,
            "git_commit_binding_verified": False,
            "merge_authority": False,
            "buyer_or_provider_acceptance": False,
            "payment_cash_or_revenue": False,
        },
    }
    if not api_key:
        base["error"] = {
            "kind": "MISSING_E2B_API_KEY",
            "message": "E2B_API_KEY is required",
        }
        return _finalize_receipt(base)

    factory = _default_sandbox_factory if sandbox_factory is None else sandbox_factory
    sandbox = None
    try:
        sandbox = factory(job.template, job.sandbox_timeout_seconds, api_key)
        base["sandbox_id"] = _sandbox_id(sandbox)
        sandbox.files.write(_ARCHIVE_REMOTE, archive_bytes)

        remote_digest = _checked_internal_stage(
            sandbox,
            "ARCHIVE_DIGEST",
            _ARCHIVE_DIGEST_SCRIPT,
            min(job.sandbox_timeout_seconds, 120),
            args=[_ARCHIVE_REMOTE],
        )
        if remote_digest != job.source_archive_sha256:
            raise ProviderExecutionError(
                "in-sandbox source archive digest mismatch"
            )

        _checked_internal_stage(
            sandbox,
            "SAFE_EXTRACT",
            _SAFE_EXTRACT_SCRIPT,
            min(job.sandbox_timeout_seconds, 180),
            args=[
                _ARCHIVE_REMOTE,
                _WORKSPACE_REMOTE,
                str(MAX_ARCHIVE_MEMBERS),
                str(MAX_ARCHIVE_MEMBER_BYTES),
                str(MAX_ARCHIVE_UNCOMPRESSED_BYTES),
            ],
        )

        if job.manifest:
            manifest_payload = [
                {"path": item.path, "sha256": item.sha256}
                for item in job.manifest
            ]
            sandbox.files.write(
                _MANIFEST_REMOTE,
                _canonical_bytes(manifest_payload),
            )
            _checked_internal_stage(
                sandbox,
                "MANIFEST",
                _MANIFEST_SCRIPT,
                min(job.sandbox_timeout_seconds, 120),
                args=[_WORKSPACE_REMOTE, _MANIFEST_REMOTE],
            )

        command_receipts: list[dict[str, Any]] = []
        for order, command in enumerate(job.commands):
            result = _provider_run(
                sandbox,
                shlex.join(command.argv),
                command.timeout_seconds,
                cwd=_WORKSPACE_REMOTE,
            )
            command_receipt = _command_result(
                result,
                order,
                command,
                secret_values,
            )
            command_receipts.append(command_receipt)
            if command_receipt["exit_code"] != 0:
                break
        base["commands"] = command_receipts
        base["green"] = (
            len(command_receipts) == len(job.commands)
            and all(item["exit_code"] == 0 for item in command_receipts)
        )
        if not base["green"]:
            base["error"] = {
                "kind": "COMMAND_FAILED",
                "message": "one command failed; later commands were not executed",
            }
    except Exception as exc:
        base["green"] = False
        base["error"] = {
            "kind": type(exc).__name__,
            "message": _excerpt(str(exc), secret_values),
        }
    finally:
        if sandbox is not None:
            base["kill_attempted"] = True
            try:
                sandbox.kill()
                base["kill_succeeded"] = True
            except Exception as exc:
                base["kill_succeeded"] = False
                if base["error"] is None:
                    base["green"] = False
                    base["error"] = {
                        "kind": "SANDBOX_KILL_FAILED",
                        "message": _excerpt(str(exc), secret_values),
                    }

    return _finalize_receipt(base)
