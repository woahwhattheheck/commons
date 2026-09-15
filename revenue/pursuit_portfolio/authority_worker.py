"""Isolated production authority worker.

This file is executed by :mod:`revenue.pursuit_portfolio.authority` with
``python -I -S``. Candidate data crosses the boundary only as bounded bytes.
The worker derives the effective-account trust root and UTC inside the isolated
child; caller-selected paths, HOME/PYTHON* environment values, module patches,
and caller clocks are not authority inputs.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    # Works both from a source checkout and site-packages:
    # <root>/revenue/pursuit_portfolio/authority_worker.py
    return Path(__file__).resolve().parents[2]


def main() -> int:
    if not sys.flags.isolated or not sys.flags.no_site:
        sys.stderr.write("authority worker requires python -I -S\n")
        return 2

    root = _repo_root()
    sys.path.insert(0, str(root))

    import base64
    from datetime import datetime, timezone
    import hashlib
    import hmac
    import json
    import os
    import re

    from revenue.pursuit_portfolio import current, floor, host
    from revenue.pursuit_portfolio.authority_protocol import (
        AUTHORITY_RUNTIME,
        MAX_WORKER_REQUEST_BYTES,
        MAX_WORKER_RESPONSE_BYTES,
        PRODUCTION_HOST_SEAL_SCHEMA,
        WORKER_REQUEST_SCHEMA,
        WORKER_RESPONSE_SCHEMA,
    )
    from revenue.pursuit_portfolio.core import MAX_FILE_BYTES, PortfolioError, load_json_bytes
    from revenue.pursuit_portfolio.current import MAX_AUTHORITY_BYTES

    b64_re = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")

    def trusted_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    def decode_field(value: object, maximum: int, where: str) -> bytes:
        if type(value) is not str or len(value) > ((maximum + 2) // 3) * 4 + 4:
            raise PortfolioError(f"{where}: bounded base64 string required")
        if b64_re.fullmatch(value) is None:
            raise PortfolioError(f"{where}: invalid base64")
        try:
            raw = base64.b64decode(value.encode("ascii"), validate=True)
        except Exception as exc:
            raise PortfolioError(f"{where}: invalid base64") from exc
        if len(raw) > maximum:
            raise PortfolioError(f"{where}: byte bound exceeded")
        return raw

    def encode_field(raw: bytes) -> str:
        return base64.b64encode(raw).decode("ascii")

    def fixed_paths() -> tuple[Path, Path]:
        trust_root = (
            host._effective_account_home()
            / ".config"
            / "commons"
            / "pursuit-portfolio"
        )
        return trust_root / "authority-key.json", trust_root / "authority-floor.json"

    def read_private(path: Path, maximum: int, where: str) -> bytes:
        parent_fd = host._open_validated_host_parent(path, where)
        try:
            return host._read_validated_host_leaf(path, parent_fd, maximum, where)
        finally:
            os.close(parent_fd)

    def load_key(key_path: Path):
        return host._parse_host_key(
            read_private(key_path, current.MAX_KEY_BYTES, "authority key")
        )

    def load_floor(floor_path: Path, key, now: str):
        raw = read_private(floor_path, floor.MAX_FLOOR_BYTES, "authority floor")
        value = floor._normalize(load_json_bytes(raw, "authority floor"))
        if raw != current._canonical(value):
            raise PortfolioError("authority floor: persisted bytes must be canonical JSON")
        if value["key_id"] != key.key_id:
            raise PortfolioError("authority floor: key_id mismatch")
        if current._dt(value["updated_at"], "authority floor.updated_at") > current._dt(
            now, "trusted_now"
        ):
            raise PortfolioError("authority floor: future-updated generation")
        expected = hmac.new(
            key.key,
            current._canonical(floor._unsigned(value)),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(value["hmac_sha256"], expected):
            raise PortfolioError("authority floor: HMAC mismatch")
        return floor.AuthorityFloor(
            authority_sha256=value["authority_sha256"],
            generation=value["generation"],
            key_id=value["key_id"],
            updated_at=value["updated_at"],
            value=value,
            raw=raw,
        )

    def seal(value, key, retained_floor):
        base = {
            "authority_floor_generation": retained_floor.generation,
            "authority_floor_sha256": hashlib.sha256(retained_floor.raw).hexdigest(),
            "authority_runtime": AUTHORITY_RUNTIME,
            "authority_sha256": hashlib.sha256(value.authority_bytes).hexdigest(),
            "current_receipt_sha256": hashlib.sha256(
                value.current_receipt_bytes
            ).hexdigest(),
            "evaluated_at": value.compiled.result["evaluated_at"],
            "input_sha256": value.compiled.result["input_sha256"],
            "key_id": key.key_id,
            "markdown_sha256": hashlib.sha256(value.compiled.markdown_bytes).hexdigest(),
            "receipt_file_sha256": hashlib.sha256(value.compiled.receipt_bytes).hexdigest(),
            "result_sha256": hashlib.sha256(value.compiled.result_bytes).hexdigest(),
            "schema": PRODUCTION_HOST_SEAL_SCHEMA,
        }
        return {
            **base,
            "hmac_sha256": hmac.new(
                key.key, current._canonical(base), hashlib.sha256
            ).hexdigest(),
        }

    seal_keys = frozenset(
        {
            "authority_floor_generation",
            "authority_floor_sha256",
            "authority_runtime",
            "authority_sha256",
            "current_receipt_sha256",
            "evaluated_at",
            "hmac_sha256",
            "input_sha256",
            "key_id",
            "markdown_sha256",
            "receipt_file_sha256",
            "result_sha256",
            "schema",
        }
    )

    def parse_seal(raw: bytes) -> dict:
        value = load_json_bytes(raw, "host seal")
        if type(value) is not dict or set(value) != set(seal_keys):
            raise PortfolioError("host seal: exact isolated-worker key set required")
        if value["schema"] != PRODUCTION_HOST_SEAL_SCHEMA:
            raise PortfolioError("host seal: isolated-worker v3 required")
        if value["authority_runtime"] != AUTHORITY_RUNTIME:
            raise PortfolioError("host seal: isolated-worker runtime binding required")
        current._token(value["key_id"], "host seal.key_id")
        current._dt(value["evaluated_at"], "host seal.evaluated_at")
        generation = value["authority_floor_generation"]
        if type(generation) is not int or type(generation) is bool or not (
            1 <= generation <= 10**12
        ):
            raise PortfolioError("host seal: invalid authority_floor_generation")
        for name in (
            "authority_floor_sha256",
            "authority_sha256",
            "current_receipt_sha256",
            "hmac_sha256",
            "input_sha256",
            "markdown_sha256",
            "receipt_file_sha256",
            "result_sha256",
        ):
            current._sha(value[name], f"host seal.{name}")
        if raw != current._canonical(value):
            raise PortfolioError("host seal: persisted bytes must be canonical JSON")
        return value

    def compile_payload(payload: dict) -> dict:
        if set(payload) != {"source", "authority"}:
            raise PortfolioError("worker compile: exact payload keys required")
        source_raw = decode_field(payload["source"], MAX_FILE_BYTES, "worker source")
        authority_raw = decode_field(
            payload["authority"], MAX_AUTHORITY_BYTES, "worker authority"
        )
        source = load_json_bytes(source_raw, "input")
        authority = load_json_bytes(authority_raw, "upstream authority")
        now = trusted_now()
        key_path, floor_path = fixed_paths()
        key = load_key(key_path)
        authorized = current._compile_authorized_at(source, authority, key, now)
        floor_before = load_floor(floor_path, key, now)
        floor.require_current_authority(floor_before, authorized.authority_bytes)
        host_seal = seal(authorized, key, floor_before)
        host_seal_bytes = current._canonical(host_seal)
        floor_after = load_floor(floor_path, key, trusted_now())
        host._same_floor(floor_before, floor_after)
        floor.require_current_authority(floor_after, authorized.authority_bytes)
        return {
            "portfolio": encode_field(authorized.compiled.result_bytes),
            "markdown": encode_field(authorized.compiled.markdown_bytes),
            "receipt": encode_field(authorized.compiled.receipt_bytes),
            "authority": encode_field(authorized.authority_bytes),
            "current_receipt": encode_field(authorized.current_receipt_bytes),
            "host_seal": encode_field(host_seal_bytes),
        }

    def verify_payload(payload: dict) -> dict:
        expected = {
            "portfolio",
            "markdown",
            "receipt",
            "authority",
            "current_receipt",
            "host_seal",
        }
        if set(payload) != expected:
            raise PortfolioError("worker verify: exact payload keys required")
        result_raw = decode_field(payload["portfolio"], MAX_FILE_BYTES, "portfolio.json")
        markdown_raw = decode_field(payload["markdown"], MAX_FILE_BYTES, "portfolio.md")
        receipt_raw = decode_field(payload["receipt"], MAX_FILE_BYTES, "receipt.json")
        authority_raw = decode_field(
            payload["authority"], MAX_AUTHORITY_BYTES, "upstream-authority.json"
        )
        current_receipt_raw = decode_field(
            payload["current_receipt"], MAX_AUTHORITY_BYTES, "current-receipt.json"
        )
        host_seal_raw = decode_field(
            payload["host_seal"], MAX_AUTHORITY_BYTES, "host-seal.json"
        )
        now = trusted_now()
        key_path, floor_path = fixed_paths()
        key = load_key(key_path)
        floor_before = load_floor(floor_path, key, now)
        floor.require_current_authority(floor_before, authority_raw)
        host_seal = parse_seal(host_seal_raw)
        if host_seal["key_id"] != key.key_id:
            raise PortfolioError("host seal: key_id mismatch")
        result = load_json_bytes(result_raw, "result")
        expected_bindings = {
            "authority_floor_generation": floor_before.generation,
            "authority_floor_sha256": hashlib.sha256(floor_before.raw).hexdigest(),
            "authority_runtime": AUTHORITY_RUNTIME,
            "authority_sha256": hashlib.sha256(authority_raw).hexdigest(),
            "current_receipt_sha256": hashlib.sha256(current_receipt_raw).hexdigest(),
            "evaluated_at": result.get("evaluated_at"),
            "input_sha256": result.get("input_sha256"),
            "key_id": key.key_id,
            "markdown_sha256": hashlib.sha256(markdown_raw).hexdigest(),
            "receipt_file_sha256": hashlib.sha256(receipt_raw).hexdigest(),
            "result_sha256": hashlib.sha256(result_raw).hexdigest(),
            "schema": PRODUCTION_HOST_SEAL_SCHEMA,
        }
        base = {name: host_seal[name] for name in expected_bindings}
        if base != expected_bindings:
            raise PortfolioError(
                "host seal: exact compiled-generation/current-floor binding mismatch"
            )
        expected_mac = hmac.new(
            key.key, current._canonical(base), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(host_seal["hmac_sha256"], expected_mac):
            raise PortfolioError("host seal: HMAC mismatch")
        verified = current._verify_authorized_at(
            result_raw,
            markdown_raw,
            receipt_raw,
            authority_raw,
            current_receipt_raw,
            key,
            now,
        )
        floor_after = load_floor(floor_path, key, trusted_now())
        host._same_floor(floor_before, floor_after)
        floor.require_current_authority(floor_after, authority_raw)
        return {
            **verified,
            "authority_floor_generation": floor_after.generation,
            "authority_floor_sha256": hashlib.sha256(floor_after.raw).hexdigest(),
            "authority_runtime": AUTHORITY_RUNTIME,
            "host_seal_sha256": hashlib.sha256(host_seal_raw).hexdigest(),
            "host_seal_verified": True,
        }

    def emit(value: dict) -> None:
        raw = (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        if len(raw) > MAX_WORKER_RESPONSE_BYTES:
            raise PortfolioError("authority worker response exceeds byte bound")
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()

    try:
        request_raw = sys.stdin.buffer.read(MAX_WORKER_REQUEST_BYTES + 1)
        if len(request_raw) > MAX_WORKER_REQUEST_BYTES:
            raise PortfolioError("authority worker request exceeds byte bound")
        request = load_json_bytes(request_raw, "authority worker request")
        if set(request) != {"schema", "operation", "payload"}:
            raise PortfolioError("authority worker request: exact key set required")
        if request["schema"] != WORKER_REQUEST_SCHEMA:
            raise PortfolioError("authority worker request: unsupported schema")
        if type(request["payload"]) is not dict:
            raise PortfolioError("authority worker request: payload object required")
        if request["operation"] == "compile":
            payload = compile_payload(request["payload"])
        elif request["operation"] == "verify":
            payload = verify_payload(request["payload"])
        else:
            raise PortfolioError("authority worker request: unsupported operation")
        emit(
            {
                "schema": WORKER_RESPONSE_SCHEMA,
                "ok": True,
                "payload": payload,
            }
        )
        return 0
    except (PortfolioError, OSError, ValueError) as exc:
        try:
            emit(
                {
                    "schema": WORKER_RESPONSE_SCHEMA,
                    "ok": False,
                    "error": str(exc),
                }
            )
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
