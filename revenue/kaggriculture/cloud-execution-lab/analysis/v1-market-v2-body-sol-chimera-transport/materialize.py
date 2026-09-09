# SPDX-License-Identifier: Apache-2.0
"""Materialize the checksum-bound SOL-CHIMERA final tree, then self-delete."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zlib

OPERATION = "titan-v3-market-chimera-causal-ablation-20260909-sol-chimera-01"
PART_COUNT = 7
ENCODED_CHARS = 84196
COMPRESSED_BYTES = 63145
RAW_BYTES = 222876
COMPRESSED_SHA256 = "bc9d5d321b9d6c1bc67276185cc71e10d0a27f09408cc729ab484d3577916f75"
RAW_SHA256 = "fb7233f62699cf4568d782217b622c90fb1b35a7b4db9d3b677500b62f50ec91"
EXPECTED = {
    ".github/workflows/titan-v3-market-chimera-sol-chimera.yml": {
        "mode": "100644",
        "sha256": "b73bcafb841d0977a095d90680b70a055b18c71994ea4033bf757c0670282803"
    },
    "p/sol-chimera-titan-v3-market-causal-ablation-20260909-01.md": {
        "mode": "100644",
        "sha256": "f42d36917f05aa205b9f7ad8aa7767ddba0c9a3edfb6d5810772a0ca1b620d21"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/README.md": {
        "mode": "100644",
        "sha256": "806e4d0e294966a86ce0c08491620db04e6cb1314e9a1cefcc8dce7acc27cffc"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/SOURCE-CONTRACT.json": {
        "mode": "100644",
        "sha256": "8596294f214daeaccd9c19fa72295cfc7dc82bb85871d738f193b9e08cf697d4"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/bundle.py": {
        "mode": "100644",
        "sha256": "4f9f30472369887c69f17796534219f39bc3aa2b1e281923f5b18dd2dabdf9bb"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/candidate.py": {
        "mode": "100644",
        "sha256": "a1ef0d6608ef4d60be91a25319e55bd118c79d28d0b3244619dadd01d5a5497f"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/compare.py": {
        "mode": "100644",
        "sha256": "d58149b7216d5ad1eb8c782d07974533a8d85c19f3bb1f14cfe1e02d5d07f6ca"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/materialize_evaluator.py": {
        "mode": "100644",
        "sha256": "49bfb4cb4302b7120860313cef9453d6808865584e66d6bc2ad5c69e2043a14d"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/run_tests.sh": {
        "mode": "100755",
        "sha256": "d2d66cf2c27cc119c67a86eec6e942c6042aaacad6323c89c12f8964e800732c"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/test_bundle.py": {
        "mode": "100644",
        "sha256": "97ba93de3b02dc242da927c96b5d180513de78b8509461f5acaf8fcfceba7760"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/test_candidate.py": {
        "mode": "100644",
        "sha256": "52da84975307f43f129037417ef83fed21abc031e9da5f1c428fc3b1fbd8fb03"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/test_compare.py": {
        "mode": "100644",
        "sha256": "a7654a615f0261f8018d46842ad58049dd2a8cca5664213caf8b07f14e423a1f"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/test_materialize_evaluator.py": {
        "mode": "100644",
        "sha256": "18d28ddef514b8c117da285b9d112ab471a33d7b61d150917c2a47619d0b5143"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/test_source_contract.py": {
        "mode": "100644",
        "sha256": "161e19a1bbcab36dcf0700e124fa82f896d5a27fea86b3b7cb24afd5626604a8"
    },
    "revenue/kaggriculture/cloud-execution-lab/analysis/v1-market-v2-body-sol-chimera/verify_source_contract.py": {
        "mode": "100644",
        "sha256": "eabbdaa1f0b7744d7363117b69cfe4fcc262a577adae04c12423f0033cb2f188"
    }
}
BOOTSTRAP_WORKFLOW = ".github/workflows/titan-v3-market-chimera-bootstrap-sol-chimera.yml"


class TransportError(RuntimeError):
    pass


def reject_constant(value: str) -> None:
    raise TransportError(f"non-finite payload constant: {value}")


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TransportError(f"duplicate payload key: {key}")
        result[key] = value
    return result


def repo_root(start: Path) -> Path:
    for parent in (start, *start.parents):
        if (parent / ".git").exists():
            return parent.resolve(strict=True)
    raise TransportError("repository root not found")


def safe_target(repo: Path, relative: str) -> Path:
    if not relative or "\\" in relative:
        raise TransportError(f"unsafe target path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise TransportError(f"unsafe target path: {relative}")
    target = repo.joinpath(*pure.parts)
    resolved_parent = target.parent.resolve(strict=True) if target.parent.exists() else None
    if resolved_parent is not None:
        try:
            resolved_parent.relative_to(repo)
        except ValueError as exc:
            raise TransportError(f"target parent escapes repository: {relative}") from exc
    return target


def decode_payload(parts_dir: Path) -> dict:
    expected_names = [f"part-{index:03d}.txt" for index in range(PART_COUNT)]
    actual = sorted(path.name for path in parts_dir.iterdir())
    if actual != expected_names:
        raise TransportError(f"payload part set mismatch: {actual}")
    encoded_parts = []
    for name in expected_names:
        path = parts_dir / name
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise TransportError(f"payload part is not a regular file: {name}")
        text = path.read_text(encoding="ascii")
        if not text.endswith("\n") or "\n" in text[:-1] or "\r" in text:
            raise TransportError(f"payload part framing mismatch: {name}")
        encoded_parts.append(text[:-1])
    encoded = "".join(encoded_parts)
    if len(encoded) != ENCODED_CHARS:
        raise TransportError("encoded payload length mismatch")
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TransportError("invalid base64 payload") from exc
    if len(compressed) != COMPRESSED_BYTES or hashlib.sha256(compressed).hexdigest() != COMPRESSED_SHA256:
        raise TransportError("compressed payload identity mismatch")
    inflater = zlib.decompressobj()
    raw = inflater.decompress(compressed, RAW_BYTES + 1)
    raw += inflater.flush()
    if (
        len(raw) != RAW_BYTES
        or inflater.unconsumed_tail
        or inflater.unused_data
        or not inflater.eof
        or hashlib.sha256(raw).hexdigest() != RAW_SHA256
    ):
        raise TransportError("raw payload identity mismatch")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransportError("invalid JSON payload") from exc
    return payload


def materialize(repo: Path, transport: Path) -> dict:
    payload = decode_payload(transport / "parts")
    if set(payload) != {"schema_version", "operation", "files"}:
        raise TransportError("payload top-level keys mismatch")
    if payload["schema_version"] != 1 or payload["operation"] != OPERATION:
        raise TransportError("payload identity mismatch")
    files = payload["files"]
    if not isinstance(files, dict) or set(files) != set(EXPECTED):
        raise TransportError("payload file set mismatch")

    decoded = {}
    for relative in sorted(EXPECTED):
        row = files[relative]
        expected = EXPECTED[relative]
        if not isinstance(row, dict) or set(row) != {"mode", "bytes", "sha256", "content_b64"}:
            raise TransportError(f"payload row mismatch: {relative}")
        if row["mode"] != expected["mode"] or row["sha256"] != expected["sha256"]:
            raise TransportError(f"payload manifest drift: {relative}")
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise TransportError(f"payload byte count malformed: {relative}")
        try:
            data = base64.b64decode(row["content_b64"], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise TransportError(f"payload file base64 invalid: {relative}") from exc
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise TransportError(f"payload file identity mismatch: {relative}")
        target = safe_target(repo, relative)
        if target.exists() or target.is_symlink():
            raise TransportError(f"final target unexpectedly exists: {relative}")
        decoded[relative] = data

    written = []
    try:
        for relative, data in decoded.items():
            target = safe_target(repo, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, 0o755 if EXPECTED[relative]["mode"] == "100755" else 0o644)
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            written.append(target)
    except Exception:
        for target in reversed(written):
            target.unlink(missing_ok=True)
        raise

    for relative, expected in EXPECTED.items():
        target = safe_target(repo, relative)
        data = target.read_bytes()
        mode = "100755" if os.access(target, os.X_OK) else "100644"
        if hashlib.sha256(data).hexdigest() != expected["sha256"] or mode != expected["mode"]:
            raise TransportError(f"post-write identity mismatch: {relative}")

    bootstrap = safe_target(repo, BOOTSTRAP_WORKFLOW)
    if not bootstrap.is_file() or bootstrap.is_symlink():
        raise TransportError("bootstrap workflow identity missing")
    bootstrap.unlink()
    shutil.rmtree(transport)
    return {
        "operation": OPERATION,
        "final_files": len(EXPECTED),
        "compressed_sha256": COMPRESSED_SHA256,
        "raw_sha256": RAW_SHA256,
    }


def main() -> int:
    transport = Path(__file__).resolve().parent
    repo = repo_root(transport)
    receipt = materialize(repo, transport)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
